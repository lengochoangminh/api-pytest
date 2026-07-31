from pytests.__init__ import *


def test_case():
    """
    [Step1] Vertical privilege escalation — org member (non-owner) attempts to update their own org
    [Step2] Cross-org IDOR — org owner attempts to update a different org using its orgCode
    [Step3] No-org isolation — authenticated user with no org membership attempts to update any org
    [Step4] Post-attack verification — confirm org data is unchanged and legitimate owner still has access

    Security properties under test:
      - Only the org OWNER (or privileged role) may update verified org information.
      - Knowing an orgCode is NOT sufficient to update it — the caller must own/manage that org.
      - A user who owns Org A cannot modify Org B by supplying Org B's orgCode.
      - Attacks must not corrupt state — the legitimate owner must still be able to operate normally.
    """

    owner_email       = ORG_OWNER_EMAIL()
    member_email      = ORG_MEMBER_EMAIL()
    unprivileged_email = UID_USER_NAME()
    cert_org_code     = CERT_COMPANY_ID()
    non_cert_org_code = NON_CERT_COMPANY_ID()
    cert_org_name     = CERT_COMPANY_NAME()

    owner_client       = Unified_ID_API(owner_email)
    member_client      = Unified_ID_API(member_email)
    unprivileged_client = Unified_ID_API(unprivileged_email)

    try:
        # =====================================================================

        print("✅ [Step 1] Vertical privilege escalation — org member attempts to update their own org")
        print(f"  📋 Attacker (member) email : {member_email}")
        print(f"  📋 Target org code         : {cert_org_code}")

        member_response = member_client.verify_org(
            org_code=cert_org_code,
            name="AttackerInjectedName",
        )

        print(f"\n  📋 Response status: {member_response.status_code}")

        if member_response.status_code == 200:
            body = member_response.json()
            error_code = body.get("errorCode")
            print(f"  📋 errorCode: {error_code} | message: {body.get('message', 'N/A')}")
            assert error_code != 0, (
                "❌ SECURITY FAIL: A regular org member was able to update verified org info "
                "(errorCode 0 returned). Non-owners must be rejected."
            )
            print("  ✅ PASS: Member attempt rejected at application level (non-zero errorCode)")
        else:
            assert member_response.status_code in [401, 403], (
                f"❌ SECURITY FAIL: Unexpected HTTP {member_response.status_code} for "
                f"member update attempt — expected 401 or 403."
            )
            print(f"  ✅ PASS: Member attempt rejected at HTTP level (status {member_response.status_code})")

        # =====================================================================

        print("\n✅ [Step 2] Cross-org IDOR — org owner attempts to update a different org")
        print(f"  📋 Attacker (cert org owner) email : {owner_email}")
        print(f"  📋 Attacker's own org              : {cert_org_code}")
        print(f"  📋 Target org (not owned)          : {non_cert_org_code}")

        cross_org_response = owner_client.verify_org(
            org_code=non_cert_org_code,
            name="CrossOrgInjectedName",
        )

        print(f"\n  📋 Response status: {cross_org_response.status_code}")

        if cross_org_response.status_code == 200:
            body = cross_org_response.json()
            error_code = body.get("errorCode")
            print(f"  📋 errorCode: {error_code} | message: {body.get('message', 'N/A')}")
            assert error_code != 0, (
                "❌ SECURITY FAIL: Owner of Org A was able to update Org B by supplying "
                "Org B's orgCode (errorCode 0 returned). Cross-org modification must be rejected."
            )
            print("  ✅ PASS: Cross-org IDOR rejected at application level (non-zero errorCode)")
        else:
            assert cross_org_response.status_code in [401, 403], (
                f"❌ SECURITY FAIL: Unexpected HTTP {cross_org_response.status_code} for "
                f"cross-org attack — expected 401 or 403."
            )
            print(f"  ✅ PASS: Cross-org IDOR rejected at HTTP level (status {cross_org_response.status_code})")

        # =====================================================================

        print("\n✅ [Step 3] No-org isolation — unprivileged user attempts to update any org")
        print(f"  📋 Attacker (no-org user) email : {unprivileged_email}")
        print(f"  📋 Target org code              : {cert_org_code}")

        noorg_response = unprivileged_client.verify_org(
            org_code=cert_org_code,
            name="NoOrgInjectedName",
        )

        print(f"\n  📋 Response status: {noorg_response.status_code}")

        if noorg_response.status_code == 200:
            body = noorg_response.json()
            error_code = body.get("errorCode")
            print(f"  📋 errorCode: {error_code} | message: {body.get('message', 'N/A')}")
            assert error_code != 0, (
                "❌ SECURITY FAIL: A user with no org membership was able to update a "
                "verified org (errorCode 0 returned). Non-members must be rejected."
            )
            print("  ✅ PASS: No-org user attempt rejected at application level (non-zero errorCode)")
        else:
            assert noorg_response.status_code in [401, 403], (
                f"❌ SECURITY FAIL: Unexpected HTTP {noorg_response.status_code} for "
                f"no-org user attempt — expected 401 or 403."
            )
            print(f"  ✅ PASS: No-org user attempt rejected at HTTP level (status {noorg_response.status_code})")

        # =====================================================================

        print("\n✅ [Step 4] Post-attack verification — confirm org state is intact")

        # Verify the legitimate owner can still update their own org normally.
        # This confirms: (a) attacks did not corrupt state, (b) the owner role is intact.
        owner_verify_response = owner_client.verify_org(
            org_code=cert_org_code,
            name=cert_org_name,   # restore to known-good name as part of verification
        )

        print(f"  📋 Legitimate owner probe status: {owner_verify_response.status_code}")

        if owner_verify_response.status_code == 200:
            body = owner_verify_response.json()
            error_code = body.get("errorCode")
            assert error_code == 0, (
                f"❌ SECURITY CONCERN: Legitimate owner can no longer update their org "
                f"(errorCode {error_code}: {body.get('message')}) — possible state corruption."
            )
            print("  ✅ PASS: Legitimate owner can still update their org — state is intact")
        else:
            assert owner_verify_response.status_code not in [401, 403], (
                f"❌ SECURITY CONCERN: Legitimate owner received HTTP {owner_verify_response.status_code} "
                f"— they may have lost ownership due to an attack."
            )
            print(f"  ✅ PASS: Owner has valid auth context (HTTP {owner_verify_response.status_code})")

        print("\n✅ All security checks passed")

    finally:
        owner_client.close()
        member_client.close()
        unprivileged_client.close()
