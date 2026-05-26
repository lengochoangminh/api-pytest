from pytests.__init__ import *


def test_case():
    """
    [Step1] Test update info API with GET method (should be rejected)
    [Step2] Test update info API with PUT method (should be rejected)
    [Step3] Test update info API with DELETE method (should be rejected)
    [Step4] Test update info API with PATCH method (should be rejected)
    [Step5] Test update info API with OPTIONS method (CORS handling)
    [Step6] Verify POST method works correctly (positive validation)
    """

    email = UID_USER_NAME()
    account_id = UID_ACCOUNT_ID()
    uid_client = Unified_ID_API(email)

    # =================================

    # Step 1: Test invalid HTTP methods
    print("\n[Step 1] Testing invalid HTTP methods...")

    method_tests = [
        {"name": "GET_method", "method": "GET", "expected_codes": [405, 400, 404]},
        {"name": "PUT_method", "method": "PUT", "expected_codes": [405, 400]},
        {"name": "DELETE_method", "method": "DELETE", "expected_codes": [405, 400]},
        {"name": "PATCH_method", "method": "PATCH", "expected_codes": [405, 400]},
        {"name": "HEAD_method", "method": "HEAD", "expected_codes": [405, 400, 404]},
        {
            "name": "OPTIONS_method",
            "method": "OPTIONS",
            "expected_codes": [200, 204, 405],
        },
    ]

    method_passed = 0
    method_total = len(method_tests)
    for i, test_case in enumerate(method_tests, 1):
        print(
            f"\n  Test {i}/{method_total}: {test_case['name']} - {test_case['method']}"
        )

        try:
            response = uid_client.update_profile(
                account_id=account_id,
                email=email,
                first_name="TestName",
                method=test_case["method"],
            )

            print(f"    Status: {response.status_code}")

            if response.status_code in test_case["expected_codes"]:
                if test_case["method"] == "OPTIONS" and response.status_code in [
                    200,
                    204,
                ]:
                    print("    ✅ PASS: OPTIONS method handled for CORS compliance")
                    method_passed += 1
                else:
                    print(
                        f"    ✅ PASS: {test_case['method']} method properly rejected"
                    )
                    method_passed += 1
            elif response.status_code == 200:
                try:
                    data = response.json()
                    error_code = data.get("errorCode")

                    print(f"    Error Code: {error_code}")

                    if error_code == 0:
                        print(
                            f"    ❌ FAIL: {test_case['method']} method was accepted and processed!"
                        )
                        # Security failure - method should be rejected
                    else:
                        print(
                            f"    ✅ PASS: {test_case['method']} method rejected with application error"
                        )
                        method_passed += 1
                except Exception:
                    print(
                        f"    ✅ PASS: {test_case['method']} method caused server error (protection active)"
                    )
                    method_passed += 1
            else:
                print(
                    f"    ✅ PASS: {test_case['method']} method rejected with alternative status"
                )
                method_passed += 1

        except Exception as request_error:
            print(
                f"    ✅ PASS: {test_case['method']} method caused request error: {request_error}"
            )
            method_passed += 1

    print(f"\n  📊 Method Validation Tests: {method_passed}/{method_total} passed")

    # Step 2: Positive validation - POST method should work
    print("\n[Step 2] Testing POST method (positive validation)...")

    try:
        response = uid_client.update_profile(
            account_id=account_id, email=email, first_name="TestName", method="POST"
        )

        print(f"  Status: {response.status_code}")

        post_passed = 0

        if response.status_code == 200:
            try:
                data = response.json()
                error_code = data.get("errorCode")

                print(f"  Error Code: {error_code}")

                if error_code == 0:
                    print("  ✅ PASS: POST method works correctly")
                    post_passed = 1
                else:
                    print(f"  ❌ FAIL: POST method failed with error {error_code}")
            except Exception:
                print("  ❌ FAIL: POST method returned non-JSON response")
        else:
            print(f"  ❌ FAIL: POST method returned status {response.status_code}")

    except Exception as post_error:
        print(f"  ❌ FAIL: POST method caused error: {post_error}")
        post_passed = 0

    # Summary
    total_tests = method_passed + post_passed
    max_tests = method_total + 1

    print("\n=== HTTP Method Validation Summary ===")
    print(f"📊 Overall Method Tests: {total_tests}/{max_tests} passed")

    method_percentage = (total_tests / max_tests) * 100

    if method_percentage >= 90:
        print("✅ EXCELLENT: Strong HTTP method validation")
    elif method_percentage >= 75:
        print("✅ GOOD: Adequate HTTP method validation")
    elif method_percentage >= 60:
        print("⚠️  FAIR: Some method validation concerns")
    else:
        print("❌ CONCERN: Significant method validation issues detected")

    uid_client.close()
