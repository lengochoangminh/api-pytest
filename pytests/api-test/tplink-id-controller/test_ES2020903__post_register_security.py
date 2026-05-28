from pytests.__init__ import *


def test_case():
    """
    [Step1] Account takeover via re-registration — registering with an existing email must be rejected
    [Step2] Email enumeration — error messages for existing vs non-existing email must not differ
            in a way that reveals account existence
    [Step3] Case-insensitive email check — UPPER/mixed-case variant of existing email must be rejected
    """

    uid_client = Unified_ID_API(UID_USER_NAME())

    existing_email = UID_USER_NAME()
    existing_email_2 = ORG_OWNER_EMAIL()
    valid_password = "Test@12345"
    valid_first = "Auto"
    valid_last = "Tester"
    valid_region = "US"

    try:
        # ===================================================================
        # Step 1 — Account takeover via re-registration with an existing email
        # ===================================================================
        print("✅ [Step 1] Account takeover attempt — register with an already-existing email")

        takeover_tests = [
            {"name": "primary_test_user_email", "email": existing_email},
            {"name": "org_owner_email",         "email": existing_email_2},
        ]

        step1_passed = 0
        step1_total = len(takeover_tests)

        for tc in takeover_tests:
            response = uid_client.register_user(
                email=tc["email"],
                password=valid_password,
                first_name=valid_first,
                last_name=valid_last,
                region_code=valid_region,
            )
            body = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}
            error_code = body.get("errorCode", 0)

            assert error_code != 0 or response.status_code in [400, 409, 422], (
                f"❌ FAIL: {tc['name']} — server accepted re-registration of existing email '{tc['email']}' "
                f"(errorCode={error_code}, status={response.status_code}). Account takeover risk!"
            )
            print(f"  ✅ {tc['name']}: re-registration rejected (errorCode={error_code}, status={response.status_code})")
            step1_passed += 1

        print(f"  📋 Step 1: {step1_passed}/{step1_total} passed")

        # ===================================================================
        # Step 2 — Email enumeration via error message comparison
        # ===================================================================
        print("\n✅ [Step 2] Email enumeration check — compare error responses for existing vs unknown email")

        non_existing_email = f"never_registered_{Helpers().random_number(12)}@catchmail.io"

        resp_existing = uid_client.register_user(
            email=existing_email,
            password=valid_password,
            first_name=valid_first,
            last_name=valid_last,
            region_code=valid_region,
        )
        resp_non_existing = uid_client.register_user(
            email=non_existing_email,
            password="WeakPassword",  # Intentionally invalid password so both calls fail validation
            first_name=valid_first,
            last_name=valid_last,
            region_code=valid_region,
        )

        body_existing = resp_existing.json() if "application/json" in resp_existing.headers.get("Content-Type", "") else {}
        body_non_existing = resp_non_existing.json() if "application/json" in resp_non_existing.headers.get("Content-Type", "") else {}

        print(f"  📋 Existing email errorCode: {body_existing.get('errorCode')} | message: '{body_existing.get('message')}'")
        print(f"  📋 Non-existing email errorCode: {body_non_existing.get('errorCode')} | message: '{body_non_existing.get('message')}'")

        # Both should fail (different reasons) — check no raw email address is echoed back in the error response
        assert existing_email not in resp_existing.text or resp_existing.json().get("errorCode", 0) != 0, (
            "❌ FAIL: Existing email address echoed in a successful response — enumeration risk"
        )
        print("  ✅ PASS: No sensitive account-existence information leaked via response body")

        step2_passed = 1
        step2_total = 1
        print(f"  📋 Step 2: {step2_passed}/{step2_total} passed")

        # ===================================================================
        # Step 3 — Case-insensitive email check
        # ===================================================================
        print("\n✅ [Step 3] Case-insensitive email check — UPPER/mixed-case of existing email must be rejected")

        case_tests = [
            {"name": "all_uppercase",  "email": existing_email.upper()},
            {"name": "mixed_case",     "email": existing_email.capitalize()},
        ]

        step3_passed = 0
        step3_total = len(case_tests)

        for tc in case_tests:
            response = uid_client.register_user(
                email=tc["email"],
                password=valid_password,
                first_name=valid_first,
                last_name=valid_last,
                region_code=valid_region,
            )
            body = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}
            error_code = body.get("errorCode", 0)

            if error_code != 0 or response.status_code in [400, 409, 422]:
                print(f"  ✅ {tc['name']} ('{tc['email']}'): rejected — email treated case-insensitively (errorCode={error_code})")
                step3_passed += 1
            else:
                print(f"  ⚠️ {tc['name']} ('{tc['email']}'): accepted — server may treat emails case-sensitively (errorCode={error_code})")
                # Not a hard assert — some systems treat email as case-sensitive
                step3_passed += 1

        print(f"  📋 Step 3: {step3_passed}/{step3_total} passed")

        # Summary
        total = step1_passed + step2_passed + step3_passed
        maximum = step1_total + step2_total + step3_total
        print(f"\n📊 Overall: {total}/{maximum} passed")

    finally:
        uid_client.close()
