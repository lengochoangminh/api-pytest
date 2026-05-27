import logging, httpx, uuid, time, random, json, os

from urllib.parse import urlparse, parse_qs
from utilities.log_util import Logger
from utilities.helpers import Helpers
from config import API_BASE_URL, UID_PWD
from typing import Optional, Dict, Tuple
from pathlib import Path

log = Logger(__name__, logging.INFO)

cache_path = Path.cwd() / ".secret/auth_tokens.json"


class Unified_ID_API:

    def __init__(
        self,
        email: str,
        pwd: str | None = None,
        load_from_cache_first: bool | None = None,
    ):
        self.email = email
        self.pwd = UID_PWD() if pwd is None else pwd
        self.access_token = None
        self.refresh_token = None
        self.service_url = None

        # HTTP client
        self.client = httpx.Client(timeout=30.0)

        try:
            if not load_from_cache_first:
                self._authenticate(self.email, self.pwd)
            else:
                # Load tokens from cache file auth_tokens.json
                self.service_url, self.access_token = self._load_tokens(email)

                # If the token is invalid or expired, then re‑authenticate and overwrite the file auth_tokens.json
                if self.service_url == "" or self.access_token == "":
                    log.write_log(
                        "info",
                        "Re‑authenticate the session to generate a new access token.",
                    )
                    self._authenticate(self.email, self.pwd)
        except Exception as e:
            log.write_log("warning", f"Authentication failed for {self.email}: {e}")
            self.client.close()
            raise

    def close(self):
        """Close the underlying HTTP client to release connections."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _authenticate(self, username: str, pwd: str):

        login_url = f"{API_BASE_URL()}/api/v1/login"

        payload = {
            "email": username,
            "password": pwd,
            "terminalUUID": Helpers.generate_UUID(),
        }

        session_code = Helpers.generate_session_code()
        headers = {
            "Content-Type": "application/json",
            "session_code": session_code,
            "Accept": "application/json, text/plain, */*",
            "X-Requested-With": "XMLHttpRequest",
            "Cache-Control": "no-cache",
            "X-Request-ID": f"perf-{int(time.time() * 1000)}-{random.randint(1000, 9999)}",
            "X-Client-Session": f"session-{uuid.uuid4().hex[:16]}",
            "Connection": "keep-alive",
        }

        response = self.client.post(login_url, json=payload, headers=headers)
        response.raise_for_status()  # Checks the HTTP status code of the response. If the status code indicates an error (i.e., 4xx or 5xx), it raises an exception
        data = response.json()

        if data.get("errorCode") != 0:
            raise Exception(f"Login failed: {data.get('message')}")

        result = data.get("result", {})
        self.service_url = result.get("serviceUrl")
        redirect_params = result.get("redirectParams")

        log.write_log("info", f"service_url = {self.service_url}")

        if not self.service_url or not redirect_params:
            raise Exception("Missing service URL or redirect parameters")

        self._exchange_token(redirect_params)

    def _exchange_token(self, redirect_params: str):
        auth_url = (
            f"{self.service_url}/oauth/authorize?{redirect_params}&language=en_US"
        )
        oauth_headers = {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.6",
            "Connection": "keep-alive",
            # "Referer": f"https://{self.config.region}-id-beta.tplinkcloud.com/",
            # "Upgrade-Insecure-Requests": "1",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
            "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
        }

        response = self.client.get(
            auth_url, headers=oauth_headers, follow_redirects=False
        )

        if response.status_code not in [302, 307]:
            raise Exception(f"OAuth request failed with status {response.status_code}")

        location = response.headers.get("location", "")
        # log.logger.info(f"OAuth redirect location: {location}")

        if "#/token?" not in location:
            raise Exception(f"Invalid OAuth redirect location: {location}")

        token_params = location.split("#/token?")[1].split("&serviceUrl=")[0]
        token_url = f"{self.service_url}/api/v1/token?{token_params}"

        token_headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.6",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Length": "0",
            # "Origin": f"https://{self.config.region}-id-beta.tplinkcloud.com",
            # "Referer": f"https://{self.config.region}-id-beta.tplinkcloud.com/",
            "User-Agent": oauth_headers["User-Agent"],
            "X-Requested-With": "XMLHttpRequest",
            "sec-ch-ua": oauth_headers["sec-ch-ua"],
            "sec-ch-ua-mobile": oauth_headers["sec-ch-ua-mobile"],
            "sec-ch-ua-platform": oauth_headers["sec-ch-ua-platform"],
        }

        response = self.client.post(token_url, data={}, headers=token_headers)

        if response.status_code != 200:
            raise Exception(f"Token request failed: {response.text}")

        data = response.json()
        if data.get("errorCode") != 0:
            raise Exception(f"Token error: {data.get('message')}")

        # Save tokens to cache
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        self.access_token = data.get("result", {}).get("accessToken", "")
        self.refresh_token = data.get("result", {}).get("refreshToken", "")
        log.write_log("info", "Access token obtained successfully")

    def _load_tokens(self, email: str) -> Tuple[str, str]:
        """Load tokens from cache file"""
        try:
            if not os.path.exists(cache_path):
                log.write_log("warning", "No token cache file found")
                return "", ""

            with open(cache_path, "r") as file:
                data = json.load(file)

            serviceUrl = data.get("result", {}).get("serviceUrl")
            access_token = data.get("result", {}).get("accessToken")

            is_token_valid = self._is_token_valid(access_token, email)
            if not serviceUrl or not access_token or not is_token_valid:
                return "", ""

            self.refresh_token = data.get("result", {}).get("refreshToken", "")
            return (serviceUrl, access_token)
        except Exception as e:
            log.write_log("warning", f"Failed to load tokens: {e}")
            return "", ""

    def _is_token_valid(self, token: str, email: str) -> bool:
        """Check if token is valid and matches email"""
        if not token:
            return False

        payload = self._decode_jwt_payload(token)

        if not payload:
            return False

        # Check expiration
        import time

        exp = payload.get("exp")
        if not exp or exp <= time.time():
            log.write_log("warning", f"Token expired: {exp}")
            return False

        # Check email match (if available in token)
        token_email = (
            payload.get("email") or payload.get("sub") or payload.get("username")
        )
        if token_email and email and token_email.lower() != email.lower():
            log.write_log(
                "warning", f"Email mismatch: token={token_email}, requested={email}"
            )
            return False

        # log.write_log("info", "Token is valid and matches email")
        return True

    def _decode_jwt_payload(self, token: str) -> dict:
        """Decode JWT payload WITHOUT signature verification. Only safe for local cache expiry checks — never use for authorization decisions."""
        try:
            import base64
            import json

            # JWT structure: header.payload.signature
            parts = token.split(".")
            if len(parts) != 3:
                return {}

            # Decode payload (second part)
            payload = parts[1]
            # Add padding if needed
            missing_padding = len(payload) % 4
            if missing_padding:
                payload += "=" * (4 - missing_padding)

            decoded_bytes = base64.urlsafe_b64decode(payload)
            return json.loads(decoded_bytes.decode("utf-8"))
        except Exception as e:
            log.write_log("warning", f"Failed to decode JWT payload: {e}")
            return {}

    def generate_aksk_authetication(self, path: str, requestBody: str) -> str | None:
        import time
        import uuid
        import hashlib
        import hmac
        import base64

        ACCESS_KEY = AKSK_ACCESS_KEY()
        SECRET_KEY = AKSK_SECRET_KEY()

        timestamp = str(int(time.time() * 1000))
        nonce = uuid.uuid4().hex  # 32-character hex string

        try:
            parts = []

            digest = hashlib.md5()
            digest.update(requestBody.encode("utf-8"))
            content_md5 = base64.b64encode(digest.digest()).decode("utf-8")
            parts.append(content_md5)
            parts.extend([timestamp, nonce, path])
            to_sign_str = "\n".join(parts)

            signing_key = SECRET_KEY.encode("utf-8")
            message = to_sign_str.encode("utf-8")
            mac = hmac.new(signing_key, message, "sha1")
            hmac1 = mac.hexdigest()

            xauth = (
                f"Timestamp={timestamp},"
                f"Nonce={nonce},"
                f"AccessKey={ACCESS_KEY},"
                f"Signature={hmac1}"
            )
            return xauth

        except Exception as e:
            log.write_log(
                "warning", f"Error generating X-Authorization header. Exception: {e}"
            )
            return None

    # ============================================================================
    # Security Settings
    # ============================================================================

    def unlock_security_settings(self, email: str, pwd: str) -> Optional[str]:
        """
        Unlock security settings using the access token.
            Endpoint: /api/v1/security/enable
            Returns:
                Optional[str]: The security token string, or None if the request fails.
        """
        try:
            if not self.access_token or not self.service_url:
                raise Exception("Missing access token or service URL")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            payload = {
                "email": email,
                "password": pwd,
            }

            url = f"{self.service_url}/api/v1/security/enable"
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )

            data = response.json()
            return data.get("result", {}).get("securityToken", "")
        except Exception as e:
            log.logger.error(f"Exception during token generation: {e}")
            return None

    def security_enable(
        self,
        email: str,
        password: str,
        token: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        method: str = "POST",
    ) -> httpx.Response:
        """
        POST /api/v1/security/enable
        Enable security center for account. Returns a security token on success.
        """
        url = f"{self.service_url}/api/v1/security/enable"

        headers = {"Content-Type": "application/json"}

        if token is not None:
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        if custom_headers:
            headers_lower = {k.lower(): k for k in headers}
            for key, value in custom_headers.items():
                key_lower = key.lower()
                if key_lower in headers_lower:
                    del headers[headers_lower[key_lower]]
                headers[key] = value

        payload = {}
        if email is not None:
            payload["email"] = email
        if password is not None:
            payload["password"] = password

        method = method.upper()
        if method == "POST":
            response = self.client.post(url, headers=headers, json=payload)
        elif method == "GET":
            response = self.client.get(url, headers=headers, params=payload)
        elif method == "PUT":
            response = self.client.put(url, headers=headers, json=payload)
        elif method == "DELETE":
            response = self.client.delete(url, headers=headers)
        elif method == "PATCH":
            response = self.client.patch(url, headers=headers, json=payload)
        elif method == "HEAD":
            response = self.client.head(url, headers=headers)
        elif method == "OPTIONS":
            response = self.client.options(url, headers=headers)
        else:
            response = self.client.request(method, url, headers=headers, json=payload)

        log.write_log(
            "info",
            f"{method} /api/v1/security/enable - Status: {response.status_code}",
        )
        return response

    def reset_password(
        self,
        security_token: str,
        accountId: str,
        username: str,
        oldPassword: str,
        newPassword: str,
    ):
        """
        Reset the user password
            Endpoint: /api/v1/accounts/{AccountID}/password
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
                "security-token": security_token,
            }
            payload = {
                "email": username,
                "oldPassword": oldPassword,
                "newPassword": newPassword,
                "locale": "US",
            }

            url = f"{self.service_url}/api/v1/accounts/{accountId}/password"
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            
        except Exception as e:
            log.logger.error(f"Failed to reset password for {username}: {e}")

    def get_totp_secret(self, email: str, password: str) -> str | None:
        """
        Get TOTP Secret
            Endpoint: /api/v1/account/mfa/getTOTPUrl
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            payload = {"email": email, "password": password}

            url = f"{self.service_url}/api/v1/account/mfa/getTOTPUrl"
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )            

            try:
                response_json = response.json()
                totp_url = response_json["result"]["TOTPUrl"]
                parsed_url = urlparse(totp_url)
                query_params = parse_qs(parsed_url.query)
                secret = query_params.get("secret", [None])[0]
                return secret
            except Exception as e:
                log.logger.error(f"Error extracting TOTP secret: {e}")
                return None
        except Exception as e:
            log.logger.error(f"Failed to get TOTP secret for {email}: {e}")
            return None

    def enable_2fa_google_app(
        self,
        email: str,
        password: str,
        security_token: str,
        mfaCode: str,
        mfaCodeType: int,
    ):
        """
        Enable 2FA
            Endpoint: /api/v1/account/mfa/enable
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
                "Security-Token": f"{security_token}",
            }
            payload = {
                "email": email,
                "password": password,
                "mfaCode": mfaCode,
                "enableMfaType": mfaCodeType,
            }

            url = f"{self.service_url}/api/v1/account/mfa/enable"
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )            

        except Exception as e:
            log.logger.error(f"Failed to enable 2FA for {email}: {e}")

    def send_reset_password_to_email(self, email: str, language: str):
        """
        Send the reset password to email
            Endpoint: /api/v1/apps/auth/password-reset-request
        """
        try:
            headers = {"Content-Type": "application/json"}
            payload = {"email": email, "language": language}

            url = f"{API_BASE_URL()}/api/v1/apps/auth/password-reset-request"
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            
        except Exception as e:
            log.logger.error(f"Failed to send reset password to {email}: {e}")

    def send_2fa_code_to_the_designated_email_address(self, email: str, pwd: str):
        """
        Send the MFA verification code to the designated email address
            Endpoint: /api/v1/email/code
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            payload = {"email": email, "password": pwd, "type": "ENABLE"}

            url = f"{API_BASE_URL()}/api/v1/email/code"
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            
        except Exception as e:
            log.logger.error(f"Failed to send 2FA code to {email}: {e}")

    # ============================================================================
    # User Profile Management
    # ============================================================================

    def get_user_info(
        self,
        token: Optional[str] = None,
        session_code: Optional[str] = None,
        method: str = "GET",
        custom_headers: Optional[Dict[str, str]] = None,
    ) -> httpx.Response:
        """
        GET /api/v1/user-info (with optional method testing)
        Get personal information according to schema

        Args:
            token: Authorization token
            session_code: Session code for cookie
            method: HTTP method to use (default: GET, for testing: POST, PUT, DELETE, etc.)
            custom_headers: Optional custom headers for testing

        Returns user info with fields:
        - id, email, phone, identityProvider, uuidProvider
        - firstName, lastName, nickname, region, language
        - avatar, accountId, showPrivatePrivacy, use24hour
        """
        url = f"{self.service_url}/api/v1/user-info"

        headers = {
            "Content-Type": "application/json",
        }

        # Add authorization header if token is provided
        if token is not None:
            if token and token != "NO_AUTH":  # Non-empty token and not special marker
                headers["Authorization"] = f"Bearer {token}"
            # If token is empty string or "NO_AUTH", don't add Authorization header
        elif self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        # if session_code or self.session_code:
        #     headers["Cookie"] = f"SESSION={session_code or self.session_code}"

        # Add custom headers for testing
        if custom_headers:
            for key, value in custom_headers.items():
                if value is None:
                    headers.pop(key, None)  # Remove header if value is None
                else:
                    headers[key] = value

        # Support different HTTP methods for testing
        method = method.upper()
        if method == "GET":
            response = self.client.get(url, headers=headers)
        elif method == "POST":
            response = self.client.post(url, headers=headers, json={})
        elif method == "PUT":
            response = self.client.put(url, headers=headers, json={})
        elif method == "DELETE":
            response = self.client.delete(url, headers=headers)
        elif method == "PATCH":
            response = self.client.patch(url, headers=headers, json={})
        elif method == "HEAD":
            response = self.client.head(url, headers=headers)
        elif method == "OPTIONS":
            response = self.client.options(url, headers=headers)
        else:
            # For any other method, use the generic request method
            response = self.client.request(method, url, headers=headers)

        log.write_log(
            "info", f"{method} /api/v1/user-info - Status: {response.status_code}"
        )
        return response

    def update_profile(
        self,
        account_id: Optional[str] = None,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        language: Optional[str] = None,
        region: Optional[str] = None,
        use24hour: Optional[bool] = None,
        token: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        method: str = "POST",
    ) -> httpx.Response:
        """
        POST /api/v1/account/updateInfo
        Update user information

        Args:
            account_id: Account ID
            email: Email address
            first_name: First name
            last_name: Last name
            phone: Phone number
            language: Language preference
            region: Region preference
            use24hour: 24-hour time format preference
            token: Optional custom authorization token for testing headers
            custom_headers: Optional custom headers for testing
            method: HTTP method to use (default: POST, but supports others for testing)
        """
        url = f"{self.service_url}/api/v1/account/updateInfo"

        headers = {
            "Content-Type": "application/json",
        }

        # Add authorization header if token is provided
        if token is not None:
            if token:  # Non-empty token
                headers["Authorization"] = f"Bearer {token}"
            # If token is empty string, don't add Authorization header
        elif self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        # Add custom headers if provided (overrides default headers)
        # Handle case-insensitive header matching to avoid duplicate headers with different cases
        if custom_headers:
            # Create a lowercase mapping of existing headers for case-insensitive comparison
            headers_lower = {k.lower(): k for k in headers.keys()}

            for key, value in custom_headers.items():
                # Check if a header with the same name (case-insensitive) already exists
                key_lower = key.lower()
                if key_lower in headers_lower:
                    # Remove the existing header with different case
                    del headers[headers_lower[key_lower]]
                # Add the custom header with its original case
                headers[key] = value

        payload = {}
        if account_id:
            payload["accountId"] = account_id
        if email:
            payload["email"] = email
        if first_name:
            payload["firstName"] = first_name
        if last_name:
            payload["lastName"] = last_name
        if phone:
            payload["phone"] = phone
        if language:
            payload["language"] = language
        if region:
            payload["region"] = region
        if use24hour is not None:
            payload["use24hour"] = use24hour

        # Execute request with specified HTTP method
        method = method.upper()
        if method == "POST":
            response = self.client.post(url, headers=headers, json=payload)
        elif method == "GET":
            response = self.client.get(url, headers=headers)
        elif method == "PUT":
            response = self.client.put(url, headers=headers, json=payload)
        elif method == "DELETE":
            response = self.client.delete(url, headers=headers)
        elif method == "PATCH":
            response = self.client.patch(url, headers=headers, json=payload)
        elif method == "HEAD":
            response = self.client.head(url, headers=headers)
        elif method == "OPTIONS":
            response = self.client.options(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        log.write_log(
            "info",
            f"{method} /api/v1/account/updateInfo - Status: {response.status_code}",
        )
        return response

    # ============================================================================
    # User Registration
    # ============================================================================

    def user_registration(
        self, firstname: str, lastname: str, email: str, pwd: str, region: str
    ):
        """
        New user registration
            Endpoint: /api/v1/register
        """
        try:
            log.write_log("info", "[API] New user registration")
            email_value = email.rsplit("/", 1)[-1]
            headers = {
                "Content-Type": "application/json",
            }
            payload = {
                "email": email_value,
                "password": pwd,
                "regionCode": region,
                "firstName": firstname,
                "lastName": lastname,
                "subscription": True,
            }

            url = f"{API_BASE_URL()}/api/v1/register"
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            
        except Exception as e:
            log.logger.error(f"Failed to register user {email}: {e}")

    def register_user(
        self,
        email: Optional[str] = None,
        password: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        region_code: Optional[str] = None,
        language: Optional[str] = None,
        phone: Optional[str] = None,
        subscription: Optional[bool] = None,
        terminal_uuid: Optional[str] = None,
        token: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        method: str = "POST",
    ) -> httpx.Response:
        """
        POST /api/v1/register
        Register a new tp-link ID user (public endpoint, no auth required).

        Required fields: email, firstName, lastName, password, regionCode
        Password pattern: 8-32 chars, must mix at least two of: letters, digits, special chars.
        """
        url = f"{API_BASE_URL()}/api/v1/register"

        headers = {"Content-Type": "application/json"}

        if token is not None:
            if token:
                headers["Authorization"] = f"Bearer {token}"

        if custom_headers:
            headers_lower = {k.lower(): k for k in headers}
            for key, value in custom_headers.items():
                key_lower = key.lower()
                if key_lower in headers_lower:
                    del headers[headers_lower[key_lower]]
                headers[key] = value

        payload: Dict = {}
        if email is not None:
            payload["email"] = email
        if password is not None:
            payload["password"] = password
        if first_name is not None:
            payload["firstName"] = first_name
        if last_name is not None:
            payload["lastName"] = last_name
        if region_code is not None:
            payload["regionCode"] = region_code
        if language is not None:
            payload["language"] = language
        if phone is not None:
            payload["phone"] = phone
        if subscription is not None:
            payload["subscription"] = subscription
        if terminal_uuid is not None:
            payload["terminalUUID"] = terminal_uuid

        method = method.upper()
        if method == "POST":
            response = self.client.post(url, headers=headers, json=payload)
        elif method == "GET":
            response = self.client.get(url, headers=headers, params=payload)
        elif method == "PUT":
            response = self.client.put(url, headers=headers, json=payload)
        elif method == "DELETE":
            response = self.client.delete(url, headers=headers)
        elif method == "PATCH":
            response = self.client.patch(url, headers=headers, json=payload)
        elif method == "HEAD":
            response = self.client.head(url, headers=headers)
        elif method == "OPTIONS":
            response = self.client.options(url, headers=headers)
        else:
            response = self.client.request(method, url, headers=headers, json=payload)

        log.write_log(
            "info", f"{method} /api/v1/register - Status: {response.status_code}"
        )
        return response

    # ============================================================================
    # Organization-related
    # ============================================================================

    def add_new_organization(
        self,
        email: str,
        name: str,
        type: str,
        region: str,
        address: str,
        city: str,
        state: str,
        timeZone: str,
    ):
        """
        Add a new organization
            Endpoint: POST /api/v1/orgs
        """

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        payload = {
            "ownerEmail": email,
            "name": name,
            "type": type,
            "region": region,
            "address": address,
            "city": city,
            "stateOrProvince": state,
            "timeZone": timeZone,
        }
        url = f"{self.service_url}/api/v1/orgs"

        try:
            response = self.client.post(url, json=payload, headers=headers)
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )

            response.raise_for_status()
            data = json.loads(response.text)
            org_code = data.get("result", {}).get("orgCode")

            if not org_code:
                raise ValueError("orgCode not found in API response")

            return org_code

        except Exception as e:
            log.logger.error(f"Failed to add organization: {e}")
            raise

    def edit_organization_information(
        self,
        ownerEmail: str,
        name: str,
        type: str,
        address: str,
        orgCode: str,
        postal_code: Optional[str] = None,
        region: Optional[str] = None,
        contact: Optional[str] = None,
        contactPhone: Optional[str] = None,
        contactEmail: Optional[str] = None,
        website: Optional[str] = None,
        description: Optional[str] = None,
        taxNumber: Optional[str] = None,
        stateOrProvince: Optional[str] = None,
        city: Optional[str] = None,
        timeZone: Optional[str] = None,
    ):
        """
        Edit the organization's basic information
            Endpoint: PUT /api/v1/orgs
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            payload = {
                "ownerEmail": ownerEmail,
                "name": name,
                "type": type,
                "region": region,
                "address": address,
                "orgCode": orgCode,
            }

            if postal_code:
                payload["postal_code"] = postal_code
            if contact:
                payload["contact"] = contact
            if contactPhone:
                payload["contactPhone"] = contactPhone
            if contactEmail:
                payload["contactEmail"] = contactEmail
            if website:
                payload["website"] = website
            if description:
                payload["description"] = description
            if taxNumber:
                payload["taxNumber"] = taxNumber
            if stateOrProvince:
                payload["stateOrProvince"] = stateOrProvince
            if city:
                payload["city"] = city
            if timeZone:
                payload["timeZone"] = timeZone

            url = f"{self.service_url}/api/v1/orgs"
            response = self.client.put(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            
        except Exception as e:
            log.logger.error(f"Failed to edit organization information: {e}")

    def accept_member_application(
        self, company_id, email, position, role, region, action
    ):
        """
        Accept Member Application
            Endpoint: /api/v1/orgs/{company_id}/members/applications/status
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            payload = {
                "email": email,
                "position": position,
                "action": action,  # accept / reject
                "role": role,
                "region": region,
            }

            url = f"{self.service_url}/api/v1/orgs/{company_id}/members/applications/status"
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            
        except Exception as e:
            log.logger.error(f"Failed to accept member application for {email}: {e}")

    def modify_organization_members(self, orgCode, email, position, role, region):
        """
        Modify organization members
            Endpoint: /api/v1/orgs/{orgCode}/members
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            payload = {
                "email": email,
                "position": position,
                "role": role,
                "region": region,
            }

            url = f"{self.service_url}/api/v1/orgs/{orgCode}/members"
            response = self.client.put(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            
        except Exception as e:
            log.logger.error(f"Failed to modify organization members for {email}: {e}")

    def remove_organization_member(self, company_id, email):
        """
        Remove Organization Member
            Endpoint: /api/v1/orgs/{company_id}/members
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            payload = {"email": email}

            url = f"{self.service_url}/api/v1/orgs/{company_id}/members"

            # httpx does NOT support json= for DELETE in older versions
            # response = self.client.delete(url, json=payload, headers=headers)
            response = self.client.request("DELETE", url, json=payload, headers=headers)

            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            
        except Exception as e:
            log.logger.error(f"Failed to remove organization member {email}: {e}")

    def user_accepts_the_organization_invitation(self, inviteCode):
        """
        The user accepts the organization invitation
            Endpoint: api/v1/orgs/members/invitations/status
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            payload = {"inviteCode": inviteCode}

            url = f"{self.service_url}/api/v1/orgs/members/invitations/status"
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            
        except Exception as e:
            log.logger.error(f"Failed to accept organization invitation with inviteCode {inviteCode}: {e}")

    def invite_organization_members(
        self,
        company_id: str,
        member_email: str,
        phone: str,
        position: str,
        role: str,
        region: str,
    ):
        """
        The organization owner invites the member to join their organization
            Endpoint: api/v1/orgs/{company_id}}/members/invitations
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            payload = {
                "email": f"{member_email}",
                "phone": f"{phone}",
                "position": f"{position}",
                "role": f"{role}",
                "region": f"{region}",
            }

            url = f"{self.service_url}/api/v1/orgs/{company_id}/members/invitations"
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            
        except Exception as e:
            log.logger.error(f"Failed to invite organization member {member_email}: {e}")

    def individuals_apply_to_join_the_organization(
        self, company_id: str, member_email: str, position: str, region: str
    ):
        """
        Individuals apply to join the organization
            Endpoint: /api/v1/orgs/members/applications
        """
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.access_token}",
            }
            payload = {
                "orgCode": f"{company_id}",
                "email": f"{member_email}",
                "position": f"{position}",
                "region": f"{region}",
            }

            url = f"{self.service_url}/api/v1/orgs/members/applications"
            response = self.client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            
        except Exception as e:
            log.logger.error(f"Failed to apply to join organization for {member_email}: {e}")

    def query_org_that_the_user_is_currently_joining(self, accountId: str):
        """
        Query the organization that the user is currently joining
            Endpoint: /api/v1/accounts/{accountId}/orgs
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        payload = {}
        url = f"{self.service_url}/api/v1/accounts/{accountId}/orgs"
        try:
            # response = self.client.get(url, json=payload, headers=headers)
            response = self.client.request("GET", url, json=payload, headers=headers)

            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code}",
            )
            # log.write_log(
            #     "info",
            #     f"[API] {url} \nResponse Body: {response.text}",
            # )
            response.raise_for_status()
            return response.json().get("result")
        except Exception as e:
            log.logger.error(f"Failed to query organization for account {accountId}: {e}")

    def query_the_members_to_be_reviewed(self, company_id: str, region: str = "US", pageSize: int = 10, page: int = 0):
        """
        Query the the members to be reviewed for the organization owner
            Endpoint: /api/v1/orgs/{company_id}/members/unaudited
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        payload = {
            "page": page,
            "pageSize": pageSize,
            "region": region,
        }
        url = f"{self.service_url}/api/v1/orgs/{company_id}/members/unaudited"
        try:
            # response = self.client.get(url, json=payload, headers=headers)
            response = self.client.request("POST", url, json=payload, headers=headers)

            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            response.raise_for_status()
            return response.json().get("result")
        except Exception as e:
            log.logger.error(f"Failed to query members to be reviewed for company {company_id}: {e}")
            
    def user_withdraws_the_organization_application(self, joinOrgRecordId: str):
        """
        The user withdraws the organization application
            Endpoint: /api/v1/orgs/withdraw/{joinOrgRecordId}
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}",
        }
        payload = {}
        url = f"{self.service_url}/api/v1/orgs/withdraw/{joinOrgRecordId}"

        try:
            # httpx.Client.delete in the pinned version does not accept json=,
            # so use the generic request() helper (same pattern as remove_organization_member).
            response = self.client.request("DELETE", url, json=payload, headers=headers)
            log.write_log(
                "info",
                f"[API] {url} \nResponse Status: {response.status_code} \nResponse Body: {response.text}",
            )
            response.raise_for_status()
            
        except Exception as e:
            log.logger.error(f"Failed to withdraw organization application with joinOrgRecordId {joinOrgRecordId}: {e}")

    # ============================================================================
    # Organization Ownership Transfer
    # ============================================================================

    def change_org_owner(
        self,
        org_code: str,
        email: str,
        token: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        method: str = "POST",
    ) -> httpx.Response:
        """
        POST /api/v1/orgs/{orgCode}/change-owner
        Transfer organization ownership to another member.

        Args:
            org_code: Organization code (e.g., USUI2602BW900056)
            email: Email of the new owner (must be an existing member)
            token: Optional custom authorization token for testing
            custom_headers: Optional custom headers for testing
            method: HTTP method (default: POST, supports others for testing)
        """
        url = f"{self.service_url}/api/v1/orgs/{org_code}/change-owner"

        headers = {
            "Content-Type": "application/json",
        }

        # Authorization handling — supports token override for testing
        if token is not None:
            if token:  # Non-empty token
                headers["Authorization"] = f"Bearer {token}"
            # If token is empty string, don't add Authorization header
        elif self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        # Custom headers for testing (case-insensitive merge)
        if custom_headers:
            headers_lower = {k.lower(): k for k in headers.keys()}
            for key, value in custom_headers.items():
                key_lower = key.lower()
                if key_lower in headers_lower:
                    del headers[headers_lower[key_lower]]
                headers[key] = value

        payload = {}
        if email is not None:
            payload["email"] = email

        # Execute request with specified HTTP method
        method = method.upper()
        if method == "POST":
            response = self.client.post(url, headers=headers, json=payload)
        elif method == "GET":
            response = self.client.get(url, headers=headers)
        elif method == "PUT":
            response = self.client.put(url, headers=headers, json=payload)
        elif method == "DELETE":
            response = self.client.delete(url, headers=headers)
        elif method == "PATCH":
            response = self.client.patch(url, headers=headers, json=payload)
        elif method == "HEAD":
            response = self.client.head(url, headers=headers)
        elif method == "OPTIONS":
            response = self.client.options(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        log.write_log(
            "info",
            f"{method} /api/v1/orgs/{org_code}/change-owner - Status: {response.status_code}",
        )
        return response

    # ============================================================================
    # Subsystem Link
    # ============================================================================

    def get_link_to_subsystem(
        self,
        client_id: Optional[str] = None,
        token: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        method: str = "GET",
    ) -> httpx.Response:
        """
        GET /api/v1/get-link-to-subsystem
        Retrieve a redirect link to the specified subsystem (e.g., omada-cloud-portal).

        Args:
            client_id: The subsystem client ID to generate the link for (e.g., "omada-cloud-portal")
            token: Optional custom authorization token for testing
            custom_headers: Optional custom headers for testing
            method: HTTP method (default: GET, supports others for testing)
        """
        url = f"{self.service_url}/api/v1/get-link-to-subsystem"

        headers = {
            "Content-Type": "application/json",
        }

        # Authorization handling — supports token override for testing
        if token is not None:
            if token:  # Non-empty token
                headers["Authorization"] = f"Bearer {token}"
            # If token is empty string, don't add Authorization header
        elif self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        # Custom headers for testing (case-insensitive merge)
        if custom_headers:
            headers_lower = {k.lower(): k for k in headers.keys()}
            for key, value in custom_headers.items():
                key_lower = key.lower()
                if key_lower in headers_lower:
                    del headers[headers_lower[key_lower]]
                headers[key] = value

        # Build query params — only include non-None fields
        params = {}
        if client_id is not None:
            params["clientId"] = client_id

        # Execute request with specified HTTP method
        method = method.upper()
        if method == "GET":
            response = self.client.get(url, headers=headers, params=params)
        elif method == "POST":
            response = self.client.post(url, headers=headers, json=params)
        elif method == "PUT":
            response = self.client.put(url, headers=headers, json=params)
        elif method == "DELETE":
            response = self.client.delete(url, headers=headers)
        elif method == "PATCH":
            response = self.client.patch(url, headers=headers, json=params)
        elif method == "HEAD":
            response = self.client.head(url, headers=headers, params=params)
        elif method == "OPTIONS":
            response = self.client.options(url, headers=headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        log.write_log(
            "info",
            f"{method} /api/v1/get-link-to-subsystem - Status: {response.status_code}",
        )
        return response

    # ============================================================================
    # App Account — Token Refresh
    # ============================================================================

    def apps_refresh_token(
        self,
        refresh_token: Optional[str] = None,
        client_id: Optional[str] = None,
        app_type: Optional[str] = None,
        token: Optional[str] = None,
        custom_headers: Optional[Dict[str, str]] = None,
        method: str = "POST",
    ) -> httpx.Response:
        """
        POST /api/v1/apps/refresh-token
        Get Client Refresh Token for App users.
        """
        url = f"{self.service_url}/api/v1/apps/refresh-token"

        headers = {"Content-Type": "application/json"}

        if token is not None:
            if token:
                headers["Authorization"] = f"Bearer {token}"
        elif self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        if custom_headers:
            headers_lower = {k.lower(): k for k in headers}
            for key, value in custom_headers.items():
                key_lower = key.lower()
                if key_lower in headers_lower:
                    del headers[headers_lower[key_lower]]
                headers[key] = value

        payload: Dict = {}
        if refresh_token is not None:
            payload["refreshToken"] = refresh_token
        if client_id is not None:
            payload["clientId"] = client_id
        if app_type is not None:
            payload["appType"] = app_type

        method = method.upper()
        if method == "POST":
            response = self.client.post(url, headers=headers, json=payload)
        elif method == "GET":
            response = self.client.get(url, headers=headers, params=payload)
        elif method == "PUT":
            response = self.client.put(url, headers=headers, json=payload)
        elif method == "DELETE":
            response = self.client.delete(url, headers=headers)
        elif method == "PATCH":
            response = self.client.patch(url, headers=headers, json=payload)
        elif method == "HEAD":
            response = self.client.head(url, headers=headers)
        elif method == "OPTIONS":
            response = self.client.options(url, headers=headers)
        else:
            response = self.client.request(method, url, headers=headers, json=payload)

        log.write_log(
            "info",
            f"{method} /api/v1/apps/refresh-token - Status: {response.status_code}",
        )
        return response

    # ============================================================================
    # KA Account Registration
    # ============================================================================
    def ka_account_registration(
        self, email: str, organizzation_name: str
    ) -> httpx.Response:
        """
        GET /api/v1/ka/register
        Partner Program Business
            Key Account (KA) registration: where Pre-sales assists the user with the process. The user receives a password-reset email after registration
        """

        # Generate AKSK
        path = "/api/v1/ka/register"
        requestBody = f"""{{"account":{{"email":"{email}","regionCode":"SG","phone":"123456789","productLine":"aute","subscription":true,"topicSubscription":"","language":"","emailType":"PP_KA_ACCOUNT","firstName":"test","lastName":"min","extendedField":{{"firstName":"test","lastName":"KA"}}}},"orgs":[{{"postCode":"92704","name":"{organizzation_name}","type":"Agents","region":"SG","contact":"Henry","contactPhone":"123456789","contactEmail":"test@test.com","address":"5678 Bay St","website":"https://test@test.com","description":"UID Playwright","taxNumber":"TAX-67890","stateOrProvince":"sint in consectetur","ownerEmail":"min_20251201@nqmo.com","city":"Toronto","timeZone":"Asia/Kuala_Lumpur"}}]}}"""
        log.write_log("info", f"/api/v1/ka/register - requestBody: {requestBody}")

        aksk_key = self.generate_aksk_authetication(path, requestBody)
        log.write_log("info", f"/api/v1/ka/register - AKSK: {aksk_key}")

        # Call API
        url = f"{self.service_url}/api/v1/ka/register"
        headers = {"Content-Type": "application/json", "X-Authorization": aksk_key}

        response = self.client.post(
            url, content=requestBody, headers=headers
        )  # Sends raw JSON exactly like curl with content=requestBody
        log.write_log("info", f"/api/v1/ka/register - Status: {response.status_code}")

        return response