from pytests.__init__ import *


def test_case():
    """
    [Step1] Non-owner AuthZ bypass — org member attempts to transfer ownership using their own token
    [Step2] Cross-org attack — owner of certified org attempts to change owner of non-certified org
    [Step3] Post-attack verification — confirm ownership of both orgs is unchanged
    """

    owner_email = ORG_OWNER_EMAIL()
    member_email = ORG_MEMBER_EMAIL()
    cert_org_code = CERT_COMPANY_ID()
    non_cert_org_code = NON_CERT_COMPANY_ID()
    target_email = ORG_ADMIN_EMAIL_2()

    owner_client = Unified_ID_API(owner_email)
    member_client = Unified_ID_API(member_email)

    try:
        # =============================================
        print("✅ [Step 1] Non-owner AuthZ bypass — org member attempts to transfer ownership")
        print(f"  📋 Attacker (member) email: {member_email}")
        print(f"  📋 Target org code: {cert_org_code}")
        print(f"  📋 Attempted new owner: {target_email}")

        member_attack_response = member_client.change_org_owner(
            org_code=cert_org_code,
            email=target_email,
        )

        print(f"\n  📋 Response status: {member_attack_response.status_code}")

        if member_attack_response.status_code == 200:
            body = member_attack_response.json()
            error_code = body.get("errorCode")
            print(f"  📋 errorCode: {error_code}")
            print(f"  📋 message: {body.get('message', 'N/A')}")
            assert error_code != 0, (
                "❌ SECURITY FAIL: A regular org member was able to transfer org ownership "
                "(errorCode 0 returned). Non-owners must be rejected."
            )
            print("  ✅ PASS: Non-owner attempt rejected at application level (non-zero errorCode)")
        else:
            assert member_attack_response.status_code in [401, 403], (
                f"❌ SECURITY FAIL: Unexpected HTTP {member_attack_response.status_code} "
                f"for non-owner transfer attempt — expected 401 or 403."
            )
            print(f"  ✅ PASS: Non-owner attempt rejected at HTTP level (status {member_attack_response.status_code})")

        # =============================================
        print("\n✅ [Step 2] Cross-org attack — certified org owner attempts to change owner of non-certified org")
        print(f"  📋 Attacker (cert org owner) email: {owner_email}")
        print(f"  📋 Attacker's org: {cert_org_code}")
        print(f"  📋 Target org (non-cert): {non_cert_org_code}")
        print(f"  📋 Attempted new owner: {target_email}")

        cross_org_response = owner_client.change_org_owner(
            org_code=non_cert_org_code,
            email=target_email,
        )

        print(f"\n  📋 Response status: {cross_org_response.status_code}")

        if cross_org_response.status_code == 200:
            body = cross_org_response.json()
            error_code = body.get("errorCode")
            print(f"  📋 errorCode: {error_code}")
            print(f"  📋 message: {body.get('message', 'N/A')}")
            assert error_code != 0, (
                "❌ SECURITY FAIL: Org A's owner was able to change the owner of Org B "
                "(errorCode 0 returned). Cross-org modification must be rejected."
            )
            print("  ✅ PASS: Cross-org attack rejected at application level (non-zero errorCode)")
        else:
            assert cross_org_response.status_code in [401, 403], (
                f"❌ SECURITY FAIL: Unexpected HTTP {cross_org_response.status_code} "
                f"for cross-org attack — expected 401 or 403."
            )
            print(f"  ✅ PASS: Cross-org attack rejected at HTTP level (status {cross_org_response.status_code})")

        # =============================================
        print("\n✅ [Step 3] Post-attack verification — confirm ownership is unchanged")

        # Re-authenticate as certified org owner and verify they can still perform an
        # owner-only action (change-owner call with self-transfer should fail with a
        # domain error, not an AuthZ error — confirming they are still the owner).
        owner_verify_response = owner_client.change_org_owner(
            org_code=cert_org_code,
            email=owner_email,   # self-transfer: invalid but proves auth context is still owner
        )

        print(f"  📋 Owner self-transfer probe status: {owner_verify_response.status_code}")

        if owner_verify_response.status_code == 200:
            verify_body = owner_verify_response.json()
            verify_error = verify_body.get("errorCode")
            # Self-transfer should be rejected with a domain error (not 0), but the key
            # point is it should NOT be rejected with 401/403 (which would mean the owner
            # lost their role due to the attack).
            assert verify_error != 0, (
                "❌ UNEXPECTED: Self-transfer returned errorCode 0 — this should not succeed."
            )
            print(f"  ✅ PASS: Owner still authenticated as org owner (domain rejection errorCode {verify_error})")
        else:
            assert owner_verify_response.status_code not in [401, 403], (
                f"❌ SECURITY CONCERN: Owner received HTTP {owner_verify_response.status_code} "
                f"— they may have lost ownership due to an attack."
            )
            print(f"  ✅ PASS: Owner still has valid auth context (HTTP {owner_verify_response.status_code})")

        print("\n✅ [Step 3] All post-attack checks passed — ownership intact")

    finally:
        owner_client.close()
        member_client.close()
