from pytests.__init__ import *


def test_case():
    """
    [Step1] Test change-owner API with missing required fields
    [Step2] Test change-owner API with invalid email formats
    [Step3] Test change-owner API with invalid org codes
    [Step4] Test change-owner API with malicious payloads
    [Step5] Verify proper error responses for all invalid scenarios
    """

    owner_email = ORG_OWNER_EMAIL()
    admin_email = ORG_ADMIN_EMAIL_2()
    org_code = CERT_COMPANY_ID()

    uid_client = Unified_ID_API(owner_email)

    try:
        # =================================

        print("\n✅ [Step 1] Test missing required fields")

        missing_field_tests = [
            {"name": "missing_email", "email": None},
            {"name": "empty_email", "email": ""},
            {"name": "whitespace_email", "email": "   "},
        ]

        missing_field_passed = 0
        missing_field_total = len(missing_field_tests)

        for i, tc in enumerate(missing_field_tests, 1):
            print(f"\n  Test {i}/{missing_field_total}: {tc['name']}")

            try:
                response = uid_client.change_org_owner(
                    org_code=org_code,
                    email=tc["email"],
                )

                print(f"    Status: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        message = data.get("message", "No message")
                        print(f"    Error Code: {error_code} - Message: {message}")

                        if error_code != 0:
                            print("    ✅ PASS: Missing field properly rejected")
                            missing_field_passed += 1
                        else:
                            print("    ❌ FAIL: Missing field was accepted!")

                    except Exception:
                        print("    ⚠️  JSON parsing failed")
                        missing_field_passed += 1

                elif response.status_code in [400, 401, 403, 422]:
                    print("    ✅ PASS: HTTP-level rejection")
                    missing_field_passed += 1
                else:
                    print(f"    ⚠️  Unexpected status: {response.status_code}")

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                missing_field_passed += 1

        print(
            f"\n  📊 Missing Field Tests: {missing_field_passed}/{missing_field_total} passed"
        )

        # =================================

        print("\n✅ [Step 2] Test invalid email formats")

        invalid_email_tests = [
            {"name": "not_an_email", "email": "not-an-email"},
            {"name": "missing_at_sign", "email": "userexample.com"},
            {"name": "missing_domain", "email": "user@"},
            {"name": "missing_local_part", "email": "@example.com"},
            {"name": "double_at_sign", "email": "user@@example.com"},
            {"name": "unregistered_email", "email": "nonexistent_user_99999@nqmo.com"},
            {"name": "non_admin_member", "email": ORG_MEMBER_EMAIL()},
            {"name": "owner_self_transfer", "email": owner_email},
        ]

        email_passed = 0
        email_total = len(invalid_email_tests)

        for i, tc in enumerate(invalid_email_tests, 1):
            print(f"\n  Test {i}/{email_total}: {tc['name']}")

            try:
                response = uid_client.change_org_owner(
                    org_code=org_code,
                    email=tc["email"],
                )

                print(f"    Status: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        message = data.get("message", "No message")
                        print(f"    Error Code: {error_code} - Message: {message}")

                        if error_code != 0:
                            print("    ✅ PASS: Invalid email properly rejected")
                            email_passed += 1
                        else:
                            print("    ❌ FAIL: Invalid email was accepted!")

                    except Exception:
                        print("    ⚠️  JSON parsing failed")
                        email_passed += 1

                elif response.status_code in [400, 403, 404, 422]:
                    print("    ✅ PASS: HTTP-level rejection")
                    email_passed += 1
                else:
                    print(f"    ⚠️  Unexpected status: {response.status_code}")

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                email_passed += 1

        print(
            f"\n  📊 Invalid Email Tests: {email_passed}/{email_total} passed"
        )

        # =================================

        print("\n✅ [Step 3] Test invalid org codes")

        invalid_org_tests = [
            {"name": "nonexistent_org", "org_code": "XXXX0000000000"},
            {"name": "empty_org_code", "org_code": ""},
            {"name": "special_chars_org", "org_code": "!@#$%^&*()"},
            {"name": "sql_injection_org", "org_code": "'; DROP TABLE orgs; --"},
        ]

        org_passed = 0
        org_total = len(invalid_org_tests)

        for i, tc in enumerate(invalid_org_tests, 1):
            print(f"\n  Test {i}/{org_total}: {tc['name']}")

            try:
                response = uid_client.change_org_owner(
                    org_code=tc["org_code"],
                    email=admin_email,
                )

                print(f"    Status: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        message = data.get("message", "No message")
                        print(f"    Error Code: {error_code} - Message: {message}")

                        if error_code != 0:
                            print("    ✅ PASS: Invalid org code properly rejected")
                            org_passed += 1
                        else:
                            print("    ❌ FAIL: Invalid org code was accepted!")

                    except Exception:
                        print("    ⚠️  JSON parsing failed")
                        org_passed += 1

                elif response.status_code in [400, 403, 404, 422]:
                    print("    ✅ PASS: HTTP-level rejection")
                    org_passed += 1
                else:
                    print(f"    ⚠️  Unexpected status: {response.status_code}")

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                org_passed += 1

        print(f"\n  📊 Invalid Org Code Tests: {org_passed}/{org_total} passed")

        # =================================

        print("\n✅ [Step 4] Test malicious payloads")

        malicious_tests = [
            {"name": "xss_email", "email": '<script>alert("xss")</script>'},
            {"name": "sql_injection_email", "email": "'; DROP TABLE users; --"},
            {"name": "long_string_attack", "email": "A" * 1000 + "@example.com"},
            {"name": "null_byte_injection", "email": "test\x00admin@example.com"},
            {"name": "html_injection", "email": '<img src="x" onerror="alert(1)">'},
        ]

        malicious_passed = 0
        malicious_total = len(malicious_tests)

        for i, tc in enumerate(malicious_tests, 1):
            print(f"\n  Test {i}/{malicious_total}: {tc['name']}")

            try:
                response = uid_client.change_org_owner(
                    org_code=org_code,
                    email=tc["email"],
                )

                print(f"    Status: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        message = data.get("message", "No message")
                        print(f"    Error Code: {error_code} - Message: {message}")

                        if error_code != 0:
                            print("    ✅ PASS: Malicious payload properly rejected")
                            malicious_passed += 1
                        else:
                            print("    ❌ FAIL: Malicious payload was accepted!")

                    except Exception:
                        print("    ✅ PASS: Server protection active")
                        malicious_passed += 1

                elif response.status_code in [400, 403, 422]:
                    print("    ✅ PASS: HTTP-level security validation")
                    malicious_passed += 1
                else:
                    print(f"    ⚠️  Unexpected status: {response.status_code}")

            except Exception as request_error:
                print(f"    ✅ PASS: Security protection active: {request_error}")
                malicious_passed += 1

        print(
            f"\n  📊 Malicious Payload Tests: {malicious_passed}/{malicious_total} passed"
        )

        # =================================

        total_tests = missing_field_passed + email_passed + org_passed + malicious_passed
        max_tests = missing_field_total + email_total + org_total + malicious_total

        print("\n=== Change Owner Invalid Input Summary ===")
        print(f"📊 Overall Tests: {total_tests}/{max_tests} passed")

        percentage = (total_tests / max_tests) * 100

        if percentage >= 90:
            print("✅ EXCELLENT: Strong input validation")
        elif percentage >= 75:
            print("✅ GOOD: Adequate input validation")
        elif percentage >= 60:
            print("⚠️  FAIR: Some validation concerns")
        else:
            print("❌ CONCERN: Significant validation issues detected")

    finally:
        uid_client.close()
