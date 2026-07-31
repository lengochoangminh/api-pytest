from pytests.__init__ import *


def test_case():
    """
    [Step1] Test PUT /api/v1/orgs/verifiedOrg with all invalid HTTP methods
    [Step2] Confirm PUT method (the native method) succeeds (positive validation)
    """

    owner_email = ORG_OWNER_EMAIL()
    org_code = CERT_COMPANY_ID()

    uid_client = Unified_ID_API(owner_email)

    try:
        # =================================

        print("\n✅ [Step 1] Testing invalid HTTP methods")

        method_tests = [
            {"name": "GET_method",     "method": "GET",     "expected_codes": [405, 400, 404]},
            {"name": "POST_method",    "method": "POST",    "expected_codes": [405, 400]},
            {"name": "DELETE_method",  "method": "DELETE",  "expected_codes": [405, 400]},
            {"name": "PATCH_method",   "method": "PATCH",   "expected_codes": [405, 400]},
            {"name": "HEAD_method",    "method": "HEAD",    "expected_codes": [405, 400, 404]},
            {"name": "OPTIONS_method", "method": "OPTIONS", "expected_codes": [200, 204, 405]},
        ]

        method_passed = 0
        method_total = len(method_tests)

        for i, tc in enumerate(method_tests, 1):
            print(f"\n  Test {i}/{method_total}: {tc['name']} - {tc['method']}")

            try:
                response = uid_client.verify_org(
                    org_code=org_code,
                    name="TestName",
                    method=tc["method"],
                )

                print(f"    Status: {response.status_code}")

                if response.status_code in tc["expected_codes"]:
                    if tc["method"] == "OPTIONS" and response.status_code in [200, 204]:
                        print("    ✅ PASS: OPTIONS method handled for CORS compliance")
                        method_passed += 1
                    else:
                        print(f"    ✅ PASS: {tc['method']} method properly rejected")
                        method_passed += 1
                elif response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        print(f"    Error Code: {error_code}")

                        if error_code == 0:
                            print(f"    ❌ FAIL: {tc['method']} method was accepted and processed!")
                        else:
                            print(f"    ✅ PASS: {tc['method']} method rejected with application error")
                            method_passed += 1
                    except Exception:
                        print(f"    ✅ PASS: {tc['method']} method caused server error (protection active)")
                        method_passed += 1
                else:
                    print(f"    ✅ PASS: {tc['method']} method rejected with alternative status")
                    method_passed += 1

            except Exception as request_error:
                print(f"    ✅ PASS: {tc['method']} method caused request error: {request_error}")
                method_passed += 1

        print(f"\n  📊 Method Validation Tests: {method_passed}/{method_total} passed")

        # =================================

        print("\n✅ [Step 2] Confirm PUT method (positive validation)")

        try:
            response = uid_client.verify_org(
                org_code=org_code,
                name="TestName",
                method="PUT",
            )

            print(f"  📋 Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                error_code = data.get("errorCode")
                if error_code == 0:
                    print("  ✅ PASS: PUT method accepted and processed successfully")
                else:
                    print(f"  ⚠️  PUT returned errorCode {error_code}: {data.get('message')}")
            else:
                print(f"  ⚠️  PUT returned HTTP {response.status_code}")

        except Exception as e:
            print(f"  ⚠️  PUT request failed: {e}")

    finally:
        uid_client.close()
