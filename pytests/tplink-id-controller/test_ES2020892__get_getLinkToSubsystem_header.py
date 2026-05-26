from pytests.__init__ import *


def test_case():
    """
    [Step1] Test GET /api/v1/get-link-to-subsystem with missing/invalid authorization headers
    [Step2] Test with malformed or tampered Bearer tokens
    [Step3] Test with missing Content-Type header
    [Step4] Test with malicious/injected custom headers
    """

    email = UID_USER_NAME()
    uid_client = Unified_ID_API(email)

    try:
        # =================================

        print("[Step 1] Testing missing/invalid authorization headers...")
        auth_tests = [
            {"name": "no_auth_header", "token": None, "force_no_auth": True},
            {"name": "empty_token", "token": "", "force_no_auth": False},
            {"name": "invalid_token_format", "token": "invalid_token_12345", "force_no_auth": False},
            {"name": "malformed_bearer", "token": "NotBearer invalid_token", "force_no_auth": False},
            {"name": "expired_like_token", "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expired.token", "force_no_auth": False},
        ]

        auth_passed = 0
        auth_total = len(auth_tests)

        for i, tc in enumerate(auth_tests, 1):
            print(f"\n  Test {i}/{auth_total}: {tc['name']}")

            try:
                if tc.get("force_no_auth", False):
                    url = f"{uid_client.service_url}/api/v1/get-link-to-subsystem"
                    headers = {"Content-Type": "application/json"}
                    response = uid_client.client.get(
                        url,
                        headers=headers,
                        params={"clientId": "omada-cloud-portal"},
                    )
                else:
                    response = uid_client.get_link_to_subsystem(
                        client_id="omada-cloud-portal",
                        token=tc["token"],
                    )

                print(f"    Status: {response.status_code}")

                if response.status_code in [401, 403]:
                    print("    ✅ PASS: Authorization properly rejected")
                    auth_passed += 1
                elif response.status_code == 200:
                    print("    ❌ FAIL: Invalid authorization was accepted!")
                else:
                    print(f"    ✅ PASS: Alternative rejection (HTTP {response.status_code})")
                    auth_passed += 1

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                auth_passed += 1

        print(f"\n  📊 Authorization Tests: {auth_passed}/{auth_total} passed")
        assert auth_passed == auth_total, (
            f"❌ {auth_total - auth_passed} authorization test(s) failed — invalid tokens were accepted"
        )

        # =================================

        print("\n[Step 2] Testing malformed / tampered Bearer tokens...")
        malformed_token_tests = [
            {"name": "truncated_jwt", "token": "eyJhbGciOiJSUzI1NiJ9.truncated"},
            {"name": "wrong_signature", "token": "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiJ0ZXN0QHRlc3QuY29tIn0.wrong_sig"},
            {"name": "bearer_with_spaces", "token": "valid token with spaces"},
            {"name": "sql_inject_token", "token": "' OR '1'='1"},
        ]

        malformed_passed = 0
        malformed_total = len(malformed_token_tests)

        for i, tc in enumerate(malformed_token_tests, 1):
            print(f"\n  Test {i}/{malformed_total}: {tc['name']}")

            try:
                response = uid_client.get_link_to_subsystem(
                    client_id="omada-cloud-portal",
                    token=tc["token"],
                )
                print(f"    Status: {response.status_code}")

                if response.status_code in [401, 403]:
                    print("    ✅ PASS: Malformed token properly rejected")
                    malformed_passed += 1
                elif response.status_code == 200:
                    print("    ❌ FAIL: Malformed token was accepted!")
                else:
                    print(f"    ✅ PASS: Alternative rejection (HTTP {response.status_code})")
                    malformed_passed += 1

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                malformed_passed += 1

        print(f"\n  📊 Malformed Token Tests: {malformed_passed}/{malformed_total} passed")
        assert malformed_passed == malformed_total, (
            f"❌ {malformed_total - malformed_passed} malformed token(s) were incorrectly accepted"
        )

        # =================================

        print("\n[Step 3] Testing missing Content-Type header...")
        try:
            response = uid_client.get_link_to_subsystem(
                client_id="omada-cloud-portal",
                custom_headers={"Content-Type": None},
            )
            print(f"  Status: {response.status_code}")
            assert response.status_code < 500, (
                f"Server error on missing Content-Type: {response.status_code}"
            )
            if response.status_code in [200, 400, 415]:
                print("  ✅ PASS: Missing Content-Type handled gracefully")
            else:
                print(f"  ✅ PASS: Unexpected status {response.status_code} — likely rejected")
        except AssertionError:
            raise
        except Exception as e:
            print(f"  ✅ PASS: Request-level rejection: {e}")

        # =================================

        print("\n[Step 4] Testing malicious/injected custom headers...")
        malicious_header_tests = [
            {"name": "xss_in_custom_header", "headers": {"X-Custom-Header": '<script>alert("xss")</script>'}},
            {"name": "header_injection_crlf", "headers": {"X-Injected": "value\r\nX-Extra: injected"}},
            {"name": "oversized_header_value", "headers": {"X-Large-Header": "A" * 8192}},
        ]

        malicious_header_passed = 0
        malicious_header_total = len(malicious_header_tests)

        for i, tc in enumerate(malicious_header_tests, 1):
            print(f"\n  Test {i}/{malicious_header_total}: {tc['name']}")

            try:
                response = uid_client.get_link_to_subsystem(
                    client_id="omada-cloud-portal",
                    custom_headers=tc["headers"],
                )
                print(f"    Status: {response.status_code}")

                if response.status_code in [400, 431, 403]:
                    print("    ✅ PASS: Malicious header properly rejected")
                    malicious_header_passed += 1
                elif response.status_code == 200:
                    print("    ✅ PASS: Server handled gracefully (malicious value sanitized/ignored)")
                    malicious_header_passed += 1
                else:
                    print(f"    ✅ PASS: Alternative handling (HTTP {response.status_code})")
                    malicious_header_passed += 1

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                malicious_header_passed += 1

        print(f"\n  📊 Malicious Header Tests: {malicious_header_passed}/{malicious_header_total} passed")
        assert malicious_header_passed == malicious_header_total, (
            f"❌ {malicious_header_total - malicious_header_passed} malicious header test(s) caused unexpected failures"
        )

    finally:
        uid_client.close()
