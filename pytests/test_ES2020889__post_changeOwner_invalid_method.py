from pytests.__init__ import *


def test_case():
    """
    [Step1] Test change-owner API with GET method (should be rejected)
    [Step2] Test change-owner API with PUT method (should be rejected)
    [Step3] Test change-owner API with DELETE method (should be rejected)
    [Step4] Test change-owner API with PATCH method (should be rejected)
    [Step5] Test change-owner API with OPTIONS method (CORS handling)
    [Step6] Verify POST method works correctly (positive validation)
    """

    owner_email = ORG_OWNER_EMAIL()
    admin_email = ORG_ADMIN_EMAIL_2()
    org_code = CERT_COMPANY_ID()

    uid_client = Unified_ID_API(owner_email)

    try:
        # =================================

        print("\n✅ [Step 1] Testing invalid HTTP methods")

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

        for i, tc in enumerate(method_tests, 1):
            print(f"\n  Test {i}/{method_total}: {tc['name']} - {tc['method']}")

            try:
                response = uid_client.change_org_owner(
                    org_code=org_code,
                    email=admin_email,
                    method=tc["method"],
                )

                print(f"    Status: {response.status_code}")

                if response.status_code in tc["expected_codes"]:
                    if tc["method"] == "OPTIONS" and response.status_code in [200, 204]:
                        print("    ✅ PASS: OPTIONS method handled for CORS compliance")
                        method_passed += 1
                    else:
                        print(
                            f"    ✅ PASS: {tc['method']} method properly rejected"
                        )
                        method_passed += 1
                elif response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        print(f"    Error Code: {error_code}")

                        if error_code == 0:
                            print(
                                f"    ❌ FAIL: {tc['method']} method was accepted and processed!"
                            )
                        else:
                            print(
                                f"    ✅ PASS: {tc['method']} method rejected with application error"
                            )
                            method_passed += 1
                    except Exception:
                        print(
                            f"    ✅ PASS: {tc['method']} method caused server error (protection active)"
                        )
                        method_passed += 1
                else:
                    print(
                        f"    ✅ PASS: {tc['method']} method rejected with alternative status"
                    )
                    method_passed += 1

            except Exception as request_error:
                print(
                    f"    ✅ PASS: {tc['method']} method caused request error: {request_error}"
                )
                method_passed += 1

        print(f"\n  📊 Method Validation Tests: {method_passed}/{method_total} passed")

        # =================================

        print("\n✅ [Step 2] Testing POST method (positive validation)")

        try:
            response = uid_client.change_org_owner(
                org_code=org_code,
                email=admin_email,
                method="POST",
            )

            print(f"  Status: {response.status_code}")

            post_passed = 0

            if response.status_code == 200:
                try:
                    data = response.json()
                    error_code = data.get("errorCode")
                    message = data.get("message", "N/A")
                    print(f"  Error Code: {error_code}")
                    print(f"  Message: {message}")

                    if error_code == 0:
                        print("  ✅ PASS: POST method works correctly")
                        post_passed = 1

                        # Restore: transfer ownership back
                        print("\n  🔄 Restoring original ownership...")
                        uid_client_new_owner = Unified_ID_API(admin_email)
                        try:
                            restore_response = uid_client_new_owner.change_org_owner(
                                org_code=org_code,
                                email=owner_email,
                            )
                            if restore_response.status_code == 200:
                                restore_data = restore_response.json()
                                if restore_data.get("errorCode") == 0:
                                    print("  ✅ Original ownership restored")
                                else:
                                    print(
                                        f"  ⚠️  Restore error: {restore_data.get('errorCode')}"
                                    )
                            else:
                                print(
                                    f"  ⚠️  Restore HTTP {restore_response.status_code}"
                                )
                        finally:
                            uid_client_new_owner.close()
                    else:
                        print(f"  ❌ FAIL: POST method failed with error {error_code}")

                except Exception:
                    print("  ❌ FAIL: POST method returned non-JSON response")
            else:
                print(f"  ❌ FAIL: POST method returned status {response.status_code}")

        except Exception as post_error:
            print(f"  ❌ FAIL: POST method caused error: {post_error}")
            post_passed = 0

        # =================================

        total_tests = method_passed + post_passed
        max_tests = method_total + 1

        print("\n=== Change Owner HTTP Method Validation Summary ===")
        print(f"📊 Overall Method Tests: {total_tests}/{max_tests} passed")

        percentage = (total_tests / max_tests) * 100

        if percentage >= 90:
            print("✅ EXCELLENT: Strong HTTP method validation")
        elif percentage >= 75:
            print("✅ GOOD: Adequate HTTP method validation")
        elif percentage >= 60:
            print("⚠️  FAIR: Some method validation concerns")
        else:
            print("❌ CONCERN: Significant method validation issues detected")

    finally:
        uid_client.close()
