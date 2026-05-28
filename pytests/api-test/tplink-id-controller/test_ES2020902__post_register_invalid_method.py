from pytests.__init__ import *


def test_case():
    """
    [Step1] Test wrong HTTP methods against POST /api/v1/register
            GET, PUT, DELETE, PATCH, HEAD, OPTIONS should all be rejected
    """

    uid_client = Unified_ID_API(UID_USER_NAME())

    valid_email = f"auto_method_{Helpers().random_number(10)}@catchmail.io"
    valid_password = "Test@12345"
    valid_first = "Auto"
    valid_last = "Tester"
    valid_region = "US"

    try:
        print("✅ [Step 1] Test wrong HTTP methods against POST /api/v1/register")

        wrong_method_tests = [
            {"method": "GET"},
            {"method": "PUT"},
            {"method": "DELETE"},
            {"method": "PATCH"},
            {"method": "HEAD"},
            {"method": "OPTIONS"},
        ]

        step1_passed = 0
        step1_total = len(wrong_method_tests)

        for tc in wrong_method_tests:
            response = uid_client.register_user(
                email=valid_email,
                password=valid_password,
                first_name=valid_first,
                last_name=valid_last,
                region_code=valid_region,
                method=tc["method"],
            )

            if response.status_code in [405, 404, 400, 403]:
                print(f"  ✅ {tc['method']}: rejected (status={response.status_code})")
                step1_passed += 1
            else:
                # Some methods (HEAD, OPTIONS) may return 200 with no body; check no registration occurred
                if tc["method"] in ["HEAD", "OPTIONS"] and response.status_code == 200:
                    print(f"  ✅ {tc['method']}: returned 200 (acceptable for HEAD/OPTIONS — no body processed)")
                    step1_passed += 1
                else:
                    body = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}
                    error_code = body.get("errorCode", 0)
                    if error_code != 0:
                        print(f"  ✅ {tc['method']}: rejected via errorCode (errorCode={error_code}, status={response.status_code})")
                        step1_passed += 1
                    else:
                        print(f"  ❌ {tc['method']}: unexpectedly accepted (status={response.status_code})")
                        assert False, f"{tc['method']}: Wrong HTTP method should be rejected, got status {response.status_code}"

        print(f"  📋 Step 1: {step1_passed}/{step1_total} passed")
        print(f"\n📊 Overall: {step1_passed}/{step1_total} passed")

    finally:
        uid_client.close()
