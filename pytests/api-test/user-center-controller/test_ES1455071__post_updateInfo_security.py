from pytests.__init__ import *


def test_case():
    """
    [Step1] IDOR — Authenticate as User A, attempt to update User B's account using User A's token
    [Step2] Verify User B's profile was not modified after the IDOR attempt
    [Step3] Identity mismatch — Submit User A's accountId with User B's email (and vice versa)
    [Step4] Verify all mismatched identity payloads are rejected
    """

    # User A — authenticated attacker
    attacker_email = UID_USER_NAME()
    attacker_account_id = UID_ACCOUNT_ID()

    # User B — victim / target account
    victim_email = ORG_MEMBER_EMAIL()
    victim_account_id = ORG_MEMBER_ACCOUNT_ID()

    attacker_client = Unified_ID_API(attacker_email)
    victim_client = Unified_ID_API(victim_email)

    try:
        # =============================================
        print("✅ [Step 1] IDOR — User A attempts to update User B's account using User A's token")
        print(f"  📋 Attacker (User A) email: {attacker_email}")
        print(f"  📋 Attacker (User A) accountId: {attacker_account_id}")
        print(f"  📋 Victim  (User B) email: {victim_email}")
        print(f"  📋 Victim  (User B) accountId: {victim_account_id}")

        # Capture victim's profile as baseline before the attack
        victim_before_response = victim_client.get_user_info()
        assert victim_before_response.status_code == 200, (
            f"Pre-condition failed: could not retrieve victim's current profile "
            f"(HTTP {victim_before_response.status_code})"
        )
        victim_before = victim_before_response.json().get("result", {})
        victim_original_first_name = victim_before.get("firstName")
        print(f"\n  📋 Victim's current firstName (baseline): '{victim_original_first_name}'")

        # Attacker submits victim's accountId + email using attacker's Bearer token
        idor_response = attacker_client.update_profile(
            account_id=victim_account_id,
            email=victim_email,
            first_name="IDOR_ATTACK",
            last_name="IDOR_ATTACK",
        )

        print(f"\n  📋 IDOR attempt — response status: {idor_response.status_code}")

        if idor_response.status_code == 200:
            idor_data = idor_response.json()
            error_code = idor_data.get("errorCode")
            print(f"  📋 Error Code: {error_code}")
            print(f"  📋 Message: {idor_data.get('message', 'N/A')}")
            assert error_code != 0, (
                "❌ SECURITY FAIL: IDOR vulnerability confirmed — "
                "User A's Bearer token was accepted to update User B's account (errorCode 0)."
            )
            print("  ✅ PASS: IDOR attempt rejected at application level (non-zero errorCode)")
        else:
            assert idor_response.status_code in [400, 401, 403], (
                f"❌ SECURITY FAIL: Unexpected HTTP {idor_response.status_code} returned "
                f"for IDOR attempt — expected 400/401/403."
            )
            print(f"  ✅ PASS: IDOR attempt rejected at HTTP level (status {idor_response.status_code})")

        # =============================================
        print("\n✅ [Step 2] Verify User B's profile was NOT modified by the IDOR attempt")

        victim_after_response = victim_client.get_user_info()
        assert victim_after_response.status_code == 200, (
            f"Post-check failed: could not retrieve victim's profile after attack "
            f"(HTTP {victim_after_response.status_code})"
        )
        victim_after = victim_after_response.json().get("result", {})
        victim_after_first_name = victim_after.get("firstName")

        assert victim_after_first_name == victim_original_first_name, (
            f"❌ SECURITY FAIL: Victim's firstName was silently changed from "
            f"'{victim_original_first_name}' to '{victim_after_first_name}'. "
            f"IDOR write succeeded even though the API appeared to reject it."
        )
        print(f"  ✅ PASS: Victim's profile is unchanged — firstName still '{victim_after_first_name}'")

        # =============================================
        print("\n✅ [Step 3] Identity mismatch — token identity vs payload identity")

        mismatch_tests = [
            {
                "name": "User A accountId + User B email (cross-email injection)",
                "account_id": attacker_account_id,
                "email": victim_email,
            },
            {
                "name": "User B accountId + User A email (cross-accountId injection)",
                "account_id": victim_account_id,
                "email": attacker_email,
            },
        ]

        for i, test in enumerate(mismatch_tests, 1):
            print(f"\n  Test {i}/{len(mismatch_tests)}: {test['name']}")
            print(f"    accountId: {test['account_id']}")
            print(f"    email:     {test['email']}")

            response = attacker_client.update_profile(
                account_id=test["account_id"],
                email=test["email"],
                first_name="MismatchAttempt",
            )

            print(f"    Response status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                error_code = data.get("errorCode")
                print(f"    Error Code: {error_code}")
                print(f"    Message: {data.get('message', 'N/A')}")
                assert error_code != 0, (
                    f"❌ SECURITY FAIL: Mismatched identity was accepted (errorCode 0) "
                    f"for case: {test['name']}"
                )
                print(f"    ✅ PASS: Mismatch rejected at application level (non-zero errorCode)")
            else:
                assert response.status_code in [400, 401, 403], (
                    f"❌ FAIL: Unexpected HTTP {response.status_code} for mismatch case: {test['name']}"
                )
                print(f"    ✅ PASS: Mismatch rejected at HTTP level (status {response.status_code})")

        # =============================================
        print("\n✅ [Step 4] All security checks passed — no IDOR or identity mismatch vulnerabilities detected")

    finally:
        attacker_client.close()
        victim_client.close()
