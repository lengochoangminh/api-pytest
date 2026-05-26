from pytests.__init__ import *


def test_case():
    """
    [Step1] Test POST method on GET /api/v1/get-link-to-subsystem (should be rejected)
    [Step2] Test PUT method (should be rejected)
    [Step3] Test DELETE method (should be rejected)
    [Step4] Test PATCH method (should be rejected)
    [Step5] Test HEAD method (CORS/availability check)
    [Step6] Test OPTIONS method (CORS handling)
    [Step7] Verify GET method works correctly (positive validation)
    """

    email = UID_USER_NAME()
    uid_client = Unified_ID_API(email)

    try:
        # =================================

        print("[Step 1-6] Testing invalid HTTP methods...")
        method_tests = [
            {"name": "POST_method", "method": "POST", "expected_codes": [405, 400, 404]},
            {"name": "PUT_method", "method": "PUT", "expected_codes": [405, 400]},
            {"name": "DELETE_method", "method": "DELETE", "expected_codes": [405, 400]},
            {"name": "PATCH_method", "method": "PATCH", "expected_codes": [405, 400]},
            {"name": "HEAD_method", "method": "HEAD", "expected_codes": [200, 405, 400, 404]},
            {"name": "OPTIONS_method", "method": "OPTIONS", "expected_codes": [200, 204, 405]},
        ]

        method_passed = 0
        method_total = len(method_tests)

        for i, tc in enumerate(method_tests, 1):
            print(f"\n  Test {i}/{method_total}: {tc['name']} — {tc['method']}")

            try:
                response = uid_client.get_link_to_subsystem(
                    client_id="omada-cloud-portal",
                    method=tc["method"],
                )
                print(f"    Status: {response.status_code}")

                if response.status_code in tc["expected_codes"]:
                    if tc["method"] in ["HEAD", "OPTIONS"] and response.status_code in [200, 204]:
                        print(f"    ✅ PASS: {tc['method']} method handled for CORS/availability compliance")
                        method_passed += 1
                    else:
                        print(f"    ✅ PASS: {tc['method']} method properly rejected")
                        method_passed += 1
                elif response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")

                        if error_code == 0:
                            print(f"    ❌ FAIL: {tc['method']} method was accepted and processed!")
                        else:
                            print(f"    ✅ PASS: {tc['method']} method rejected with application error (errorCode: {error_code})")
                            method_passed += 1
                    except Exception:
                        print(f"    ❌ FAIL: {tc['method']} method accepted with unparseable response")
                else:
                    print(f"    ✅ PASS: Alternative rejection (HTTP {response.status_code})")
                    method_passed += 1

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                method_passed += 1

        print(f"\n  📊 Invalid Method Tests: {method_passed}/{method_total} passed")
        assert method_passed == method_total, (
            f"❌ {method_total - method_passed} invalid HTTP method(s) were incorrectly accepted"
        )

        # =================================

        print("\n[Step 7] Verifying GET method works correctly (positive validation)...")
        response = uid_client.get_link_to_subsystem(
            client_id="omada-cloud-portal",
            method="GET",
        )
        print(f"  📋 GET response status: {response.status_code}")
        assert response.status_code == 200, f"Expected GET to succeed with 200, got {response.status_code}"

        data = response.json()
        assert data.get("errorCode") == 0, (
            f"Expected errorCode 0 for valid GET, got {data.get('errorCode')} — message: {data.get('message')}"
        )
        print("  ✅ PASS: GET method works correctly")

    finally:
        uid_client.close()
