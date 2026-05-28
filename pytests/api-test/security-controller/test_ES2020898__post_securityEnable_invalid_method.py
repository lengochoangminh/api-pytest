from pytests.__init__ import *


def test_case():
    """
    [Step1] Test wrong HTTP methods against POST /api/v1/security/enable
    [Step2] Confirm correct method (POST) still works
    """

    email = UID_USER_NAME()
    password = UID_PWD()
    uid_client = Unified_ID_API(email)

    try:
        # ===================================================================
        # Step 1 — Wrong HTTP methods
        # ===================================================================
        print("✅ [Step 1] Wrong HTTP methods")
        method_tests = [
            {"method": "GET", "expected_codes": [405, 400, 404]},
            {"method": "PUT", "expected_codes": [405, 400]},
            {"method": "DELETE", "expected_codes": [405, 400]},
            {"method": "PATCH", "expected_codes": [405, 400]},
            {"method": "HEAD", "expected_codes": [405, 400, 404]},
            {"method": "OPTIONS", "expected_codes": [200, 204, 405]},
        ]

        step1_passed = 0
        step1_total = len(method_tests)

        for tc in method_tests:
            response = uid_client.security_enable(
                email=email,
                password=password,
                method=tc["method"],
            )

            if response.status_code in tc["expected_codes"]:
                print(f"  ✅ {tc['method']}: status={response.status_code} (expected one of {tc['expected_codes']})")
                step1_passed += 1
            else:
                # Check if the body has a non-zero errorCode (some APIs return 200 with error)
                try:
                    body = response.json()
                    error_code = body.get("errorCode", 0)
                    if error_code != 0:
                        print(f"  ✅ {tc['method']}: status={response.status_code}, errorCode={error_code} (rejected via body)")
                        step1_passed += 1
                    else:
                        print(f"  ❌ {tc['method']}: status={response.status_code} — not in expected {tc['expected_codes']}")
                        assert False, f"{tc['method']} should be rejected, got status={response.status_code} with errorCode=0"
                except Exception:
                    print(f"  ❌ {tc['method']}: status={response.status_code} — unexpected")
                    assert False, f"{tc['method']} should be rejected, got status={response.status_code}"

        print(f"  📋 Step 1: {step1_passed}/{step1_total} passed")

        # ===================================================================
        # Step 2 — Confirm correct method (POST) works
        # ===================================================================
        print("\n✅ [Step 2] Confirm POST (correct method) works")
        response = uid_client.security_enable(
            email=email,
            password=password,
            method="POST",
        )

        assert response.status_code == 200, f"Expected HTTP 200 for POST, got {response.status_code}"
        body = response.json()
        assert body.get("errorCode") == 0, f"Expected errorCode 0 for POST, got {body.get('errorCode')} — {body.get('message')}"
        print(f"  ✅ POST: status=200, errorCode=0 — confirmed working")

        # ===================================================================
        # Summary
        # ===================================================================
        total = step1_passed + 1  # +1 for the POST confirmation
        maximum = step1_total + 1
        print(f"\n📊 Overall: {total}/{maximum} passed")

    finally:
        uid_client.close()
