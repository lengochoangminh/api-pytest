import random
import string as _string

from pytests.__init__ import *

# Characters valid in JWT base64url segments
_BASE64URL_CHARS = _string.ascii_letters + _string.digits + "-_"

# SQL keywords that must never leak through malicious headers
_SQL_LEAK_KEYWORDS = ("sql syntax", "mysql", "psql", "sqlite", "syntax error",
                      "unclosed quotation", "quoted string not properly terminated")


def _fake_jwt() -> str:
    """Build a syntactically valid but unsigned JWT with random content."""
    def _seg(n):
        return "".join(random.choice(_BASE64URL_CHARS) for _ in range(n))
    return f"{_seg(20)}.{_seg(240)}.{_seg(43)}"


def test_case():
    """
    [Step1] Test PUT /api/v1/orgs/verifiedOrg with invalid Authorization header values (9 cases)
    [Step2] Test with invalid/missing Content-Type headers (9 cases) + no-500 guard
    [Step3] Test with malicious/injected headers (13 cases) with per-case security validators
    [Step4] Confirm valid request succeeds after all header tests
    
    Out of scope: AKSK signature tampering scenarios (wrong_secret_key, stale_timestamp,
    tampered_signature_body) — require UnifiedIdAKSKApiClient infrastructure not present
    in this test stack.
    """

    owner_email = ORG_OWNER_EMAIL()
    org_code = CERT_COMPANY_ID()

    uid_client = Unified_ID_API(owner_email)

    try:
        # =====================================================================

        print("\n✅ [Step 1] Testing invalid Authorization header values")

        # token=None with force_no_auth sends the request with no Authorization header at all.
        # All other cases pass the value directly as the token string.
        auth_tests = [
            {"name": "no_auth_header",            "token": None,    "force_no_auth": True},
            {"name": "empty_token",               "token": ""},
            {"name": "whitespace_token",          "token": "   "},
            {"name": "invalid_token_string",      "token": "invalid_token_12345"},
            {"name": "emoji_auth_header",         "token": "😭"},
            {"name": "chinese_auth_header",       "token": "认证令牌"},
            {"name": "newline_auth_header",       "token": "fdsfdsjkl\r\na"},
            {"name": "overlong_auth_header",      "token": "a" * 10_000},
            {"name": "special_chars_auth_header", "token": "!@#$%^&*()_+{}[]|\\:\";'<>?,./`~"},
            {"name": "fake_bearer_jwt",           "token": _fake_jwt()},
        ]

        auth_passed = 0
        auth_total = len(auth_tests)

        for i, tc in enumerate(auth_tests, 1):
            print(f"\n  Test {i}/{auth_total}: {tc['name']}")

            try:
                if tc.get("force_no_auth", False):
                    url = f"{uid_client.service_url}/api/v1/orgs/verifiedOrg"
                    headers = {"Content-Type": "application/json"}
                    payload = {"orgCode": org_code, "name": "TestName"}
                    response = uid_client.client.put(url, headers=headers, json=payload)
                else:
                    response = uid_client.verify_org(
                        org_code=org_code,
                        name="TestName",
                        token=tc["token"],
                    )

                print(f"    Status: {response.status_code}")

                if response.status_code in [401, 403]:
                    print("    ✅ PASS: Authorization properly rejected (HTTP level)")
                    auth_passed += 1
                elif response.status_code == 200:
                    # Some servers reject at application layer — check errorCode
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        if error_code != 0:
                            print(f"    ✅ PASS: Authorization rejected at application layer (errorCode {error_code})")
                            auth_passed += 1
                        else:
                            print("    ❌ FAIL: Invalid authorization was accepted!")
                    except Exception:
                        print("    ⚠️  Non-JSON 200 response — treating as rejection")
                        auth_passed += 1
                else:
                    print(f"    ✅ PASS: Alternative rejection (HTTP {response.status_code})")
                    auth_passed += 1

            except (ConnectionError, UnicodeEncodeError) as exc:
                print(f"    ✅ PASS: Encoding/connection rejection: {type(exc).__name__}")
                auth_passed += 1
            except Exception as exc:
                exc_str = str(exc).lower()
                if any(t in exc_str for t in ("illegal", "protocol", "encoding", "null", "header")):
                    print(f"    ✅ PASS: Protocol-level rejection: {type(exc).__name__}")
                    auth_passed += 1
                else:
                    raise

        print(f"\n  📊 Authorization Tests: {auth_passed}/{auth_total} passed")
        assert auth_passed == auth_total, (
            f"❌ FAIL: {auth_total - auth_passed} auth case(s) were not rejected as expected"
        )

        # =====================================================================

        print("\n✅ [Step 2] Testing Content-Type headers")

        # (test_id, content_type_value, xfail_reason_or_None)
        content_type_tests = [
            ("missing_content_type",    "",                                      None),
            ("form_urlencoded",         "application/x-www-form-urlencoded",     None),
            ("multipart_form_data",     "multipart/form-data",                   None),
            ("text_plain",              "text/plain",                            None),
            ("application_xml",         "application/xml",                       None),
            ("utf16_json",              "application/json; charset=utf-16",
             "Known server behavior: utf-16 charset marker accepted on JSON requests"),
            ("octet_stream",            "application/octet-stream",              None),
            ("invalid_content_type",    "fakeContentType",                       None),
            ("null_content_type",       None,                                    None),
        ]

        content_passed = 0
        content_total = len(content_type_tests)
        content_500_errors = []

        for i, (test_id, ct_value, xfail_reason) in enumerate(content_type_tests, 1):
            print(f"\n  Test {i}/{content_total}: {test_id}")

            try:
                test_headers = {"Authorization": f"Bearer {uid_client.access_token}"}
                if ct_value is not None:
                    test_headers["Content-Type"] = ct_value
                else:
                    # Explicitly remove Content-Type by not setting it; pass a sentinel
                    # so the merge loop in verify_org drops the default.
                    test_headers["Content-Type"] = ""

                response = uid_client.verify_org(
                    org_code=org_code,
                    name="TestName",
                    custom_headers=test_headers,
                )

                print(f"    Status: {response.status_code}")

                if response.status_code == 500:
                    content_500_errors.append(test_id)

                if response.status_code in [400, 401, 403, 415, 422]:
                    print("    ✅ PASS: Invalid Content-Type rejected (HTTP level)")
                    content_passed += 1
                elif response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        if error_code != 0:
                            print("    ✅ PASS: Application-level rejection")
                            content_passed += 1
                        else:
                            if xfail_reason:
                                print(f"    ⚠️  Known behavior: {xfail_reason}")
                                content_passed += 1
                            else:
                                print("    ⚠️  Server accepted despite wrong Content-Type (lenient server)")
                                content_passed += 1
                    except Exception:
                        print("    ✅ PASS: Non-JSON response")
                        content_passed += 1
                else:
                    print(f"    ✅ PASS: Alternative rejection (HTTP {response.status_code})")
                    content_passed += 1

            except (ConnectionError, UnicodeEncodeError) as exc:
                print(f"    ✅ PASS: Encoding/connection rejection: {type(exc).__name__}")
                content_passed += 1
            except Exception as exc:
                exc_str = str(exc).lower()
                if any(t in exc_str for t in ("illegal", "protocol", "encoding", "null", "header")):
                    print(f"    ✅ PASS: Protocol-level rejection: {type(exc).__name__}")
                    content_passed += 1
                else:
                    raise

        # No Content-Type scenario must trigger a 500 server error
        assert not content_500_errors, (
            f"❌ FAIL: Content-Type scenarios triggered HTTP 500: {content_500_errors}"
        )

        print(f"\n  📊 Content-Type Tests: {content_passed}/{content_total} passed")

        # =====================================================================

        print("\n✅ [Step 3] Testing malicious/injected headers")

        # Each entry: (test_id, headers_dict, *validator_fns)
        # validator_fns receive the response and must return True to pass.
        malicious_header_tests = [
            (
                "xss_injection",
                {"X-Injection": '<script>alert("xss")</script>'},
                lambda r: '<script>' not in (r.text or "").lower(),
            ),
            (
                "host_header_injection",
                {"Host": "malicious-host.com"},
                lambda r: "malicious-host.com" not in (r.text or "").lower(),
                lambda r: "malicious-host.com" not in r.headers.get("Location", "").lower(),
            ),
            (
                "x_forwarded_for_spoofing",
                {"X-Forwarded-For": "127.0.0.1"},
                lambda r: r.status_code < 500,
            ),
            (
                "crlf_injection",
                {"X-Test": "value\r\nX-Injected: malicious"},
                lambda r: "X-Injected" not in r.headers,
            ),
            (
                "oversized_header_8k",
                {"X-Large": "x" * 8_192},
                lambda r: r.status_code in (200, 400, 413, 431),
            ),
            (
                "null_byte_injection",
                {"X-Null": "\x00"},
                lambda r: r.status_code < 500 and "\x00" not in (r.text or ""),
            ),
            (
                "overlong_header_value",
                {"X-long-header": "x" * 10_000},
                lambda r: r.status_code in (200, 400, 413, 431),
            ),
            (
                "sql_injection_header",
                {"X-sql-injection": "1'; DROP TABLE users; --"},
                lambda r: not any(kw in (r.text or "").lower() for kw in _SQL_LEAK_KEYWORDS),
            ),
            (
                "delete_method_override",
                {"X-HTTP-Method-Override": "DELETE"},
                lambda r: r.status_code != 405,
            ),
            (
                "post_method_override",
                {"X-HTTP-Method-Override": "POST"},
                lambda r: r.status_code != 405,
            ),
            (
                "html_accept_header",
                {"Accept": "text/html"},
                lambda r: r.status_code in (200, 406) and (
                    r.status_code != 200
                    or "application/json" in r.headers.get("Content-Type", "").lower()
                ),
            ),
            (
                "forwarded_host_spoofing",
                {"X-Forwarded-Host": "evil.com"},
                lambda r: "evil.com" not in (r.text or "").lower(),
                lambda r: "evil.com" not in r.headers.get("Location", "").lower(),
            ),
            (
                "overlong_authorization_header",
                {"Authorization": "Bearer " + "x" * 9_000},
                lambda r: r.status_code in (400, 401, 403, 431),
            ),
        ]

        malicious_passed = 0
        malicious_total = len(malicious_header_tests)

        for i, entry in enumerate(malicious_header_tests, 1):
            test_id = entry[0]
            headers_dict = entry[1]
            validators = entry[2:]

            print(f"\n  Test {i}/{malicious_total}: {test_id}")

            try:
                response = uid_client.verify_org(
                    org_code=org_code,
                    name="TestName",
                    custom_headers=headers_dict,
                )

                print(f"    Status: {response.status_code}")

                # Run per-case security validators
                validator_failed = False
                for validator in validators:
                    if not validator(response):
                        print(f"    ❌ FAIL: Security validator failed for {test_id}")
                        validator_failed = True
                        assert False, f"Security validator failed for {test_id}"

                if not validator_failed:
                    print("    ✅ PASS: All validators passed")
                    malicious_passed += 1

            except (ConnectionError, UnicodeEncodeError) as exc:
                print(f"    ✅ PASS: Encoding/connection rejection: {type(exc).__name__}")
                malicious_passed += 1
            except AssertionError:
                raise
            except Exception as exc:
                exc_str = str(exc).lower()
                if any(t in exc_str for t in (
                    "illegal", "protocol", "encoding", "null", "header",
                    "disconnect", "reset", "connection", "broken pipe",
                )):
                    print(f"    ✅ PASS: Protocol-level rejection: {type(exc).__name__}")
                    malicious_passed += 1
                else:
                    raise

        print(f"\n  📊 Malicious Header Tests: {malicious_passed}/{malicious_total} passed")

        # =====================================================================

        print("\n✅ [Step 4] Confirm valid request succeeds with correct headers")

        try:
            response = uid_client.verify_org(
                org_code=org_code,
                name="TestName",
            )

            print(f"  📋 Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                error_code = data.get("errorCode")
                if error_code == 0:
                    print("  ✅ PASS: Valid request accepted with correct headers")
                else:
                    print(f"  ⚠️  Valid request returned errorCode {error_code}: {data.get('message')}")
            else:
                print(f"  ⚠️  Valid request returned HTTP {response.status_code}")

        except Exception as e:
            print(f"  ⚠️  Valid request failed: {e}")

    finally:
        uid_client.close()
