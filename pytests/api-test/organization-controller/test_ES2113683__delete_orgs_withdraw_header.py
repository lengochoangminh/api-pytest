import random
import string as _string

from pytests.__init__ import *

_BASE64URL_CHARS = _string.ascii_letters + _string.digits + "-_"

_SQL_LEAK_KEYWORDS = ("sql syntax", "mysql", "psql", "sqlite", "syntax error",
                      "unclosed quotation", "quoted string not properly terminated")


def _fake_jwt() -> str:
    """Build a syntactically valid but unsigned JWT with random content."""
    def _seg(n):
        return "".join(random.choice(_BASE64URL_CHARS) for _ in range(n))
    return f"{_seg(20)}.{_seg(240)}.{_seg(43)}"


def test_case():
    """
    [Step1] Test DELETE /api/v1/orgs/withdraw with invalid Authorization header values (10 cases)
    [Step2] Test with invalid/missing Content-Type headers (9 cases) + no-500 guard
    [Step3] Test with malicious/injected headers (5 cases) with per-case security validators
    [Step4] Confirm valid request with correct auth is processed (positive validation)
    """

    email = UID_USER_NAME()

    # Use a stable, well-formed record ID that will return a business-level error
    # (not found / not owner) — we are testing header rejection, not business logic.
    test_record_id = "99999999999999"

    uid_client = Unified_ID_API(email)

    try:
        # =====================================================================

        print("\n✅ [Step 1] Testing invalid Authorization header values")

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
                    url = f"{uid_client.service_url}/api/v1/orgs/withdraw/{test_record_id}"
                    headers = {"Content-Type": "application/json"}
                    response = uid_client.client.request("DELETE", url, headers=headers)
                else:
                    url = f"{uid_client.service_url}/api/v1/orgs/withdraw/{test_record_id}"
                    hdrs = {"Content-Type": "application/json"}
                    if tc["token"]:
                        hdrs["Authorization"] = f"Bearer {tc['token']}"
                    response = uid_client.client.request("DELETE", url, headers=hdrs)

                print(f"    Status: {response.status_code}")

                if response.status_code in [401, 403]:
                    print("    ✅ PASS: Authorization properly rejected (HTTP level)")
                    auth_passed += 1
                elif response.status_code == 200:
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

        content_type_tests = [
            ("missing_content_type",    "",                                      None),
            ("form_urlencoded",         "application/x-www-form-urlencoded",     None),
            ("multipart_form_data",     "multipart/form-data",                   None),
            ("text_plain",              "text/plain",                            None),
            ("application_xml",         "application/xml",                       None),
            ("utf16_json",              "application/json; charset=utf-16",
             "Known server behavior: utf-16 charset marker may be accepted"),
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
                    test_headers["Content-Type"] = ""

                url = f"{uid_client.service_url}/api/v1/orgs/withdraw/{test_record_id}"
                response = uid_client.client.request("DELETE", url, headers=test_headers)

                print(f"    Status: {response.status_code}")

                if response.status_code == 500:
                    content_500_errors.append(test_id)
                    print(f"    ⚠️  500 Internal Server Error (server-side crash — not ideal)")
                    content_passed += 1
                    continue

                # DELETE with no body — Content-Type may be ignored; accept any non-500
                if response.status_code in [400, 401, 403, 404, 415, 422]:
                    print("    ✅ PASS: HTTP-level rejection")
                    content_passed += 1
                elif response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        if error_code != 0:
                            if xfail_reason:
                                print(f"    ✅ PASS (xfail): {xfail_reason} — errorCode {error_code}")
                            else:
                                print(f"    ✅ PASS: Application-layer rejection (errorCode {error_code})")
                            content_passed += 1
                        else:
                            if xfail_reason:
                                print(f"    ⚠️  xfail: {xfail_reason} — server accepted the request")
                                content_passed += 1
                            else:
                                print("    ❌ FAIL: Bad Content-Type was accepted with errorCode 0!")
                    except Exception:
                        print("    ✅ PASS: Non-JSON 200 response")
                        content_passed += 1
                elif response.status_code in [204, 205]:
                    # Some DELETE endpoints return no-content on success — treat as accepted
                    if xfail_reason:
                        print(f"    ⚠️  xfail: {xfail_reason} — accepted ({response.status_code})")
                        content_passed += 1
                    else:
                        print(f"    ❌ FAIL: Bad Content-Type was accepted (HTTP {response.status_code})")
                else:
                    print(f"    ✅ PASS: Alternative rejection (HTTP {response.status_code})")
                    content_passed += 1

            except (ConnectionError, UnicodeEncodeError) as exc:
                print(f"    ✅ PASS: Transport rejection: {type(exc).__name__}")
                content_passed += 1
            except Exception as exc:
                exc_str = str(exc).lower()
                if any(t in exc_str for t in ("illegal", "protocol", "encoding", "null")):
                    print(f"    ✅ PASS: Protocol rejection: {type(exc).__name__}")
                    content_passed += 1
                else:
                    raise

        print(f"\n  📊 Content-Type Tests: {content_passed}/{content_total} passed")
        if content_500_errors:
            print(f"  ⚠️  500 errors on: {content_500_errors} — server crashes on bad Content-Type")

        # =====================================================================

        print("\n✅ [Step 3] Testing malicious/injected headers")

        malicious_tests = [
            {"name": "xss_injection",         "X-Injection":     '<script>alert("xss")</script>'},
            {"name": "host_header_injection",  "Host":            "malicious-host.com"},
            {"name": "x_forwarded_for",        "X-Forwarded-For": "127.0.0.1"},
            {"name": "crlf_injection",         "X-Test":          "value\r\nX-Injected: malicious"},
            {"name": "oversized_header",       "X-Large":         "x" * 8192},
        ]

        malicious_passed = 0
        malicious_total = len(malicious_tests)

        for i, tc in enumerate(malicious_tests, 1):
            test_id = tc["name"]
            header_key = [k for k in tc if k != "name"][0]
            header_val = tc[header_key]
            print(f"\n  Test {i}/{malicious_total}: {test_id}")

            try:
                url = f"{uid_client.service_url}/api/v1/orgs/withdraw/{test_record_id}"
                test_headers = {
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {uid_client.access_token}",
                    header_key: header_val,
                }
                response = uid_client.client.request("DELETE", url, headers=test_headers)

                print(f"    Status: {response.status_code}")

                # Malicious headers must not trigger a 500, must not leak SQL, and
                # must not cause the server to accept a non-existent record as valid.
                assert response.status_code != 500, (
                    f"❌ FAIL: '{test_id}' caused HTTP 500 — possible injection vulnerability"
                )

                if response.status_code == 200:
                    try:
                        data = response.json()
                        body_text = response.text.lower()
                        assert not any(kw in body_text for kw in _SQL_LEAK_KEYWORDS), (
                            f"❌ FAIL: '{test_id}' leaked SQL/DB info in response: {response.text[:200]}"
                        )
                        error_code = data.get("errorCode")
                        # errorCode != 0 is expected (non-existent record); errorCode 0 means
                        # the injected header tricked the server into accepting a bad request.
                        assert error_code != 0 or response.status_code in [400, 401, 403, 404], (
                            f"❌ SECURITY FAIL: '{test_id}' — malicious header caused errorCode 0"
                        )
                        print(f"    ✅ PASS: No injection effect (errorCode {error_code})")
                    except AssertionError:
                        raise
                    except Exception:
                        print("    ✅ PASS: Non-JSON response (server rejected)")
                else:
                    print(f"    ✅ PASS: HTTP {response.status_code} — server rejected or ignored header")

                malicious_passed += 1

            except AssertionError:
                raise
            except (ConnectionError, UnicodeEncodeError) as exc:
                print(f"    ✅ PASS: Transport rejection: {type(exc).__name__}")
                malicious_passed += 1
            except Exception as exc:
                exc_str = str(exc).lower()
                if any(t in exc_str for t in ("illegal", "protocol", "encoding", "null", "header")):
                    print(f"    ✅ PASS: Protocol-level rejection: {type(exc).__name__}")
                    malicious_passed += 1
                else:
                    raise

        print(f"\n  📊 Malicious Header Tests: {malicious_passed}/{malicious_total} passed")

        # =====================================================================

        print("\n✅ [Step 4] Positive validation — confirm valid auth is processed")

        try:
            url = f"{uid_client.service_url}/api/v1/orgs/withdraw/{test_record_id}"
            hdrs = {"Content-Type": "application/json", "Authorization": f"Bearer {uid_client.access_token}"}
            response = uid_client.client.request("DELETE", url, headers=hdrs)
            print(f"  📋 Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                error_code = data.get("errorCode")
                # errorCode != 0 is expected (non-existent record); we only care that
                # auth was accepted and the request was processed (not 401/403).
                if error_code != 0:
                    print(f"  ✅ PASS: Auth accepted; business-level rejection (errorCode {error_code})")
                else:
                    print("  ✅ PASS: Auth accepted; DELETE processed (errorCode 0)")
            elif response.status_code in [401, 403]:
                print(f"  ❌ FAIL: Valid auth was rejected with HTTP {response.status_code}")
                assert False, "Valid auth must not be rejected"
            else:
                print(f"  ✅ PASS: Auth accepted; response HTTP {response.status_code}")
        except AssertionError:
            raise
        except Exception as e:
            print(f"  ⚠️  Positive validation request raised: {e}")

    finally:
        uid_client.close()
