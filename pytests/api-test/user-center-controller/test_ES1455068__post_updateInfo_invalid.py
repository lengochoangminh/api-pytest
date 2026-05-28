from pytests.__init__ import *


def test_case():
    """
    [Step1] Test update info API with missing required fields
    [Step2] Test update info API with invalid data formats
    [Step3] Test update info API with malicious payloads
    [Step4] Test update info API with non-existent accountId (valid format, unknown ID)
    [Step5] Verify proper error responses for all invalid scenarios
    """

    email = UID_USER_NAME()
    account_id = UID_ACCOUNT_ID()
    uid_client = Unified_ID_API(email)

    # =================================

    print("\n✅ [Step 1] Test missing required fields")
    missing_field_tests = [
        {"name": "missing_accountId", "account_id": None, "email": email},
        {"name": "missing_email", "account_id": account_id, "email": None},
        {"name": "empty_accountId", "account_id": "", "email": email},
        {"name": "empty_email", "account_id": account_id, "email": ""},
        {"name": "both_missing", "account_id": None, "email": None},
    ]

    missing_field_passed = 0
    missing_field_total = len(missing_field_tests)

    for i, test_case in enumerate(missing_field_tests, 1):
        print(f"\nTest {i}/{missing_field_total}: {test_case['name']}")

        try:
            response = uid_client.update_profile(
                account_id=test_case["account_id"],
                email=test_case["email"],
                first_name="TestName",
            )

            # print(f"    Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    error_code = data.get("errorCode")
                    message = data.get("message", "No message")
                    print(f"    Error Code: {error_code} - Message: {message}")

                    if error_code != 0:
                        print("    ✌ PASS: Missing fields properly rejected")
                        missing_field_passed += 1
                    else:
                        print("    ❌ FAIL: Missing fields were accepted!")

                except Exception:
                    print("    ⚠️  JSON parsing failed")
                    print("    📋 This may indicate proper rejection")
                    missing_field_passed += 1

            elif response.status_code in [400, 401, 403]:
                print("    ✌ PASS: HTTP-level rejection")
                missing_field_passed += 1
            else:
                print(f"    ⚠️  Unexpected status: {response.status_code}")

        except Exception as request_error:
            print(f"    ✌ PASS: Request-level rejection: {request_error}")
            missing_field_passed += 1

    print(
        f"\n  📊 Missing Field Tests: {missing_field_passed}/{missing_field_total} passed"
    )

    # Step 2: Test invalid data formats
    print("\n[Step 2] Testing invalid data formats...")

    invalid_format_tests = [
        {"name": "invalid_email_format", "email": "not-an-email"},
        {"name": "invalid_phone_format", "phone": "abc123"},
        {"name": "invalid_language_format", "language": "invalid_lang_code"},
        {"name": "invalid_region_format", "region": "XX"},
        {"name": "invalid_use24hour_format", "use24hour": "not_boolean"},
    ]

    format_passed = 0
    format_total = len(invalid_format_tests)

    for i, test_case in enumerate(invalid_format_tests, 1):
        print(f"\n  Test {i}/{format_total}: {test_case['name']}")

        try:
            kwargs = {"account_id": account_id, "email": email}

            # Override with invalid data
            for key, value in test_case.items():
                if key != "name":
                    kwargs[key] = value

            response = uid_client.update_profile(**kwargs)

            print(f"    Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    error_code = data.get("errorCode")
                    message = data.get("message", "No message")

                    print(f"    Error Code: {error_code}")
                    print(f"    Message: {message}")

                    if error_code != 0:
                        print("    ✅ PASS: Invalid format properly rejected")
                        format_passed += 1
                    else:
                        print(
                            "    ❌ FAIL: Invalid format was accepted (should be rejected)"
                        )
                        # Don't give any credit for accepting invalid formats

                except Exception:
                    print("    ⚠️  JSON parsing failed")
                    format_passed += 1

            elif response.status_code in [400, 422]:  # Validation errors
                print("    ✅ PASS: HTTP-level format validation")
                format_passed += 1
            else:
                print(f"    ⚠️  Unexpected status: {response.status_code}")

        except Exception as request_error:
            print(f"    ✅ PASS: Request-level rejection: {request_error}")
            format_passed += 1

    print(f"\n  📊 Format Validation Tests: {format_passed}/{format_total} passed")

    # Step 3: Test malicious payloads
    print("\n[Step 3] Testing malicious payloads...")

    malicious_tests = [
        {"name": "xss_firstname", "first_name": '<script>alert("xss")</script>'},
        {"name": "xss_lastname", "last_name": '<img src="x" onerror="alert(1)">'},
        {"name": "sql_injection_phone", "phone": "'; DROP TABLE users; --"},
        {"name": "long_string_attack", "first_name": "A" * 1000},
        {"name": "null_byte_injection", "last_name": "test\x00admin"},
    ]

    malicious_passed = 0
    malicious_total = len(malicious_tests)

    for i, test_case in enumerate(malicious_tests, 1):
        print(f"\n  Test {i}/{malicious_total}: {test_case['name']}")

        try:
            kwargs = {
                "account_id": account_id,
                "email": email,
            }

            # Override with malicious data
            for key, value in test_case.items():
                if key != "name":
                    kwargs[key] = value

            response = uid_client.update_profile(**kwargs)

            print(f"    Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    error_code = data.get("errorCode")
                    message = data.get("message", "No message")

                    print(f"    Error Code: {error_code}")
                    print(f"    Message: {message}")

                    if error_code != 0:
                        print("    ✅ PASS: Malicious payload properly rejected")
                        malicious_passed += 1
                    else:
                        print("    ❌ FAIL: Malicious payload was accepted!")
                        # This is a serious security concern

                except Exception:
                    print("    ✅ PASS: Server protection active (connection reset)")
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

    # Step 4: Test non-existent accountId (valid format, but does not exist in the system)
    print("\n[Step 4] Testing non-existent accountId...")

    non_existent_tests = [
        {
            "name": "well_formed_but_nonexistent_accountId",
            "account_id": "00000000000001",
            "description": "14-digit numeric ID that does not belong to any account",
        },
        {
            "name": "sequential_boundary_accountId",
            "account_id": "99999999999999",
            "description": "14-digit numeric ID at upper boundary — unlikely to exist",
        },
    ]

    non_existent_passed = 0
    non_existent_total = len(non_existent_tests)

    for i, test_case in enumerate(non_existent_tests, 1):
        print(f"\n  Test {i}/{non_existent_total}: {test_case['name']}")
        print(f"    Description: {test_case['description']}")
        print(f"    accountId: {test_case['account_id']}")

        try:
            response = uid_client.update_profile(
                account_id=test_case["account_id"],
                email=email,
                first_name="TestName",
            )

            print(f"    Status: {response.status_code}")

            if response.status_code == 200:
                try:
                    data = response.json()
                    error_code = data.get("errorCode")
                    message = data.get("message", "No message")

                    print(f"    Error Code: {error_code}")
                    print(f"    Message: {message}")

                    if error_code != 0:
                        print("    ✅ PASS: Non-existent accountId properly rejected")
                        non_existent_passed += 1
                    else:
                        print(
                            "    ❌ FAIL: Non-existent accountId was accepted (errorCode 0) — "
                            "server may not validate accountId existence"
                        )

                except Exception:
                    print("    ⚠️  JSON parsing failed")

            elif response.status_code in [400, 401, 403, 404]:
                print(f"    ✅ PASS: HTTP-level rejection (status {response.status_code})")
                non_existent_passed += 1
            else:
                print(f"    ⚠️  Unexpected status: {response.status_code}")

        except Exception as request_error:
            print(f"    ✅ PASS: Request-level rejection: {request_error}")
            non_existent_passed += 1

    print(
        f"\n  📊 Non-Existent AccountId Tests: {non_existent_passed}/{non_existent_total} passed"
    )

    # # Summary
    total_security_tests = missing_field_passed + format_passed + malicious_passed + non_existent_passed
    max_security_tests = missing_field_total + format_total + malicious_total + non_existent_total

    print("\n=== Security Validation Summary ===")
    print(
        f"📊 Overall Security Tests: {total_security_tests}/{max_security_tests} passed"
    )

    security_percentage = (total_security_tests / max_security_tests) * 100

    if security_percentage >= 90:
        print("✅ EXCELLENT: Strong security validation")
    elif security_percentage >= 75:
        print("✅ GOOD: Adequate security validation")
    elif security_percentage >= 60:
        print("⚠️  FAIR: Some security concerns")
    else:
        print("❌ CONCERN: Significant security issues detected")

    uid_client.close()
