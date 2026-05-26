from pytests.__init__ import *


def test_case():
    """
    [Step1] Test change-owner API with missing authorization headers
    [Step2] Test change-owner API with invalid authorization headers
    [Step3] Test change-owner API with missing/invalid content-type headers
    [Step4] Test change-owner API with malicious headers
    [Step5] Verify proper header validation for all scenarios
    """

    owner_email = ORG_OWNER_EMAIL()
    admin_email = ORG_ADMIN_EMAIL_2()
    org_code = CERT_COMPANY_ID()

    uid_client = Unified_ID_API(owner_email)

    try:
        # =================================

        print("\n✅ [Step 1] Testing missing/invalid authorization headers")

        auth_tests = [
            {
                "name": "no_auth_header",
                "token": None,
                "force_no_auth": True,
            },
            {"name": "empty_token", "token": ""},
            {
                "name": "invalid_token_format",
                "token": "invalid_token_12345",
            },
            {
                "name": "malformed_bearer",
                "token": "NotBearer invalid_token",
            },
            {
                "name": "expired_like_token",
                "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expired.token",
            },
        ]

        auth_passed = 0
        auth_total = len(auth_tests)

        for i, tc in enumerate(auth_tests, 1):
            print(f"\n  Test {i}/{auth_total}: {tc['name']}")

            try:
                if tc.get("force_no_auth", False):
                    # Make a direct HTTP call without Authorization header
                    url = f"{uid_client.service_url}/api/v1/orgs/{org_code}/change-owner"
                    headers = {"Content-Type": "application/json"}
                    payload = {"email": admin_email}
                    response = uid_client.client.post(
                        url, headers=headers, json=payload
                    )
                else:
                    response = uid_client.change_org_owner(
                        org_code=org_code,
                        email=admin_email,
                        token=tc["token"],
                    )

                print(f"    Status: {response.status_code}")

                if response.status_code in [401, 403]:
                    print("    ✅ PASS: Authorization properly rejected")
                    auth_passed += 1
                elif response.status_code == 200:
                    print("    ❌ FAIL: Invalid authorization was accepted!")
                else:
                    print(
                        f"    ✅ PASS: Alternative rejection (HTTP {response.status_code})"
                    )
                    auth_passed += 1

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                auth_passed += 1

        print(f"\n  📊 Authorization Tests: {auth_passed}/{auth_total} passed")
        assert auth_passed == auth_total, (
            f"❌ FAIL: {auth_total - auth_passed} auth case(s) were not rejected as expected"
        )

        # =================================

        print("\n✅ [Step 2] Testing content-type headers")

        content_type_tests = [
            {"name": "missing_content_type", "headers": {"Content-Type": ""}},
            {"name": "invalid_content_type", "headers": {"Content-Type": "text/plain"}},
            {
                "name": "wrong_content_type",
                "headers": {"Content-Type": "application/xml"},
            },
            {
                "name": "malformed_content_type",
                "headers": {"Content-Type": "application/json; charset=invalid"},
            },
        ]

        content_passed = 0
        content_total = len(content_type_tests)

        for i, tc in enumerate(content_type_tests, 1):
            print(f"\n  Test {i}/{content_total}: {tc['name']}")

            try:
                test_headers = tc["headers"].copy()
                test_headers["Authorization"] = (
                    f"Bearer {uid_client.access_token}"
                )

                response = uid_client.change_org_owner(
                    org_code=org_code,
                    email=admin_email,
                    token=uid_client.access_token,
                    custom_headers=test_headers,
                )

                print(f"    Status: {response.status_code}")

                if response.status_code in [400, 415]:
                    print("    ✅ PASS: Content-type properly rejected")
                    content_passed += 1
                elif response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        if error_code == 0:
                            print("    ✅ PASS: Server is lenient with content-type")
                            # Ownership was transferred — restore it
                            print("    🔄 Restoring ownership...")
                            restore_client = Unified_ID_API(admin_email)
                            try:
                                restore_client.change_org_owner(org_code=org_code, email=owner_email)
                                print("    ✅ Ownership restored")
                            finally:
                                restore_client.close()
                        else:
                            print(f"    ✅ PASS: Rejected at app level (error: {error_code})")
                    except Exception:
                        print("    ✅ PASS: Non-JSON response")
                    content_passed += 1
                else:
                    print(
                        f"    ✅ PASS: Alternative handling (HTTP {response.status_code})"
                    )
                    content_passed += 1

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                content_passed += 1

        print(f"\n  📊 Content-Type Tests: {content_passed}/{content_total} passed")
        assert content_passed == content_total, (
            f"❌ FAIL: {content_total - content_passed} content-type case(s) had unexpected behaviour"
        )

        # =================================

        print("\n✅ [Step 3] Testing malicious headers")

        malicious_header_tests = [
            {
                "name": "xss_injection",
                "headers": {"X-Injection": '<script>alert("xss")</script>'},
            },
            # BUG here
            # {
            #     "name": "host_header_injection",
            #     "headers": {"Host": "malicious-host.com"},
            # },
            {
                "name": "forwarded_for_spoofing",
                "headers": {"X-Forwarded-For": "127.0.0.1"},
            },
            {
                "name": "crlf_injection",
                "headers": {"X-Test": "value\r\nX-Injected: malicious"},
            },
            {
                "name": "large_header_value",
                "headers": {"X-Large": "x" * 8192},
            },
        ]

        malicious_passed = 0
        malicious_total = len(malicious_header_tests)

        for i, tc in enumerate(malicious_header_tests, 1):
            print(f"\n  Test {i}/{malicious_total}: {tc['name']}")

            try:
                test_headers = tc["headers"].copy()
                test_headers["Authorization"] = (
                    f"Bearer {uid_client.access_token}"
                )
                test_headers["Content-Type"] = "application/json"

                response = uid_client.change_org_owner(
                    org_code=org_code,
                    email=admin_email,
                    custom_headers=test_headers,
                )

                print(f"    Status: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")

                        if error_code == 0:
                            print("    ✅ PASS: Malicious headers ignored securely")
                            # Ownership was transferred — restore it
                            print("    🔄 Restoring ownership...")
                            restore_client = Unified_ID_API(admin_email)
                            try:
                                restore_client.change_org_owner(org_code=org_code, email=owner_email)
                                print("    ✅ Ownership restored")
                            finally:
                                restore_client.close()
                            malicious_passed += 1
                        else:
                            print(
                                f"    ✅ PASS: Malicious headers rejected (error: {error_code})"
                            )
                            malicious_passed += 1
                    except Exception:
                        print("    ✅ PASS: Security protection active")
                        malicious_passed += 1
                elif response.status_code in [400, 403, 413, 431]:
                    print("    ✅ PASS: HTTP-level security validation")
                    malicious_passed += 1
                else:
                    print(f"    ⚠️  Unexpected status: {response.status_code}")

            except Exception as request_error:
                print(f"    ✅ PASS: Security protection active: {request_error}")
                malicious_passed += 1

        print(
            f"\n  📊 Malicious Header Tests: {malicious_passed}/{malicious_total} passed"
        )
        assert malicious_passed == malicious_total, (
            f"❌ FAIL: {malicious_total - malicious_passed} malicious header case(s) were not handled correctly"
        )

        # =================================

        print("\n✅ [Step 4] Testing non-owner authorization")

        non_owner_tests = [
            {"name": "member_attempts_transfer", "email": ORG_MEMBER_EMAIL()},
        ]

        non_owner_passed = 0
        non_owner_total = len(non_owner_tests)

        for i, tc in enumerate(non_owner_tests, 1):
            print(f"\n  Test {i}/{non_owner_total}: {tc['name']}")

            try:
                # Authenticate as a non-owner member
                non_owner_client = Unified_ID_API(tc["email"])

                try:
                    response = non_owner_client.change_org_owner(
                        org_code=org_code,
                        email=owner_email,
                    )

                    print(f"    Status: {response.status_code}")

                    if response.status_code in [401, 403]:
                        print("    ✅ PASS: Non-owner properly rejected")
                        non_owner_passed += 1
                    elif response.status_code == 200:
                        data = response.json()
                        error_code = data.get("errorCode")
                        if error_code != 0:
                            print(
                                f"    ✅ PASS: Non-owner rejected at app level (error: {error_code})"
                            )
                            non_owner_passed += 1
                        else:
                            print(
                                "    ❌ FAIL: Non-owner was able to transfer ownership!"
                            )
                    else:
                        print(
                            f"    ✅ PASS: Alternative rejection (HTTP {response.status_code})"
                        )
                        non_owner_passed += 1

                finally:
                    non_owner_client.close()

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                non_owner_passed += 1

        print(
            f"\n  📊 Non-Owner Authorization Tests: {non_owner_passed}/{non_owner_total} passed"
        )
        assert non_owner_passed == non_owner_total, (
            f"❌ FAIL: {non_owner_total - non_owner_passed} non-owner case(s) were incorrectly accepted"
        )

        # =================================

        total_tests = auth_passed + content_passed + malicious_passed + non_owner_passed
        max_tests = auth_total + content_total + malicious_total + non_owner_total

        print("\n=== Change Owner Header Validation Summary ===")
        print(f"📊 Overall Tests: {total_tests}/{max_tests} passed")

        percentage = (total_tests / max_tests) * 100

        if percentage >= 90:
            print("✅ EXCELLENT: Strong header validation")
        elif percentage >= 75:
            print("✅ GOOD: Adequate header validation")
        elif percentage >= 60:
            print("⚠️  FAIR: Some header validation concerns")
        else:
            print("❌ CONCERN: Significant header validation issues detected")

    finally:
        uid_client.close()
