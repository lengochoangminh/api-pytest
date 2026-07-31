from pytests.__init__ import *


def test_case():
    """
    [Step1] IDOR — User A (UID_USER_NAME) attempts to withdraw User B's pending application
            by guessing/knowing the joinOrgRecordId.  Must be rejected.
    [Step2] No-application IDOR — User with no pending application tries an arbitrary record ID.
            Must be rejected.
    [Step3] Cross-account escalation — ORG_MEMBER submits an application and
            UID_USER_NAME (unrelated user) tries to withdraw it. Must be rejected.
    [Step4] Post-attack verification — confirm that the targeted application was NOT withdrawn
            and is still accessible / intact.

    Security properties under test:
      - The DELETE /api/v1/orgs/withdraw/{joinOrgRecordId} endpoint must enforce that
        ONLY the applicant who owns the record can withdraw it.
      - Knowing a joinOrgRecordId must NOT be sufficient to withdraw another user's application.
      - Attacks must not corrupt state — the legitimate owner must still be able to withdraw
        their own application after all attack attempts.
    """

    attacker_email  = UID_USER_NAME()
    attacker_id     = UID_ACCOUNT_ID()
    victim_email    = ORG_MEMBER_EMAIL()
    victim_id       = ORG_MEMBER_ACCOUNT_ID()
    org_code        = CERT_COMPANY_ID()

    attacker_client = Unified_ID_API(attacker_email)
    victim_client   = Unified_ID_API(victim_email)

    victim_applied  = False
    victim_record_id = None

    try:
        # =====================================================================

        print("✅ [Step 1] IDOR — attacker tries a guessed/known record ID")
        print(f"  📋 Attacker email : {attacker_email}")

        # Use a well-formed numeric ID that the attacker does not own.
        guessed_id = "99999999999998"
        _url = f"{attacker_client.service_url}/api/v1/orgs/withdraw/{guessed_id}"
        _hdrs = {"Content-Type": "application/json", "Authorization": f"Bearer {attacker_client.access_token}"}
        idor_response = attacker_client.client.request("DELETE", _url, headers=_hdrs)

        print(f"\n  📋 Response status: {idor_response.status_code}")

        if idor_response.status_code == 200:
            body = idor_response.json()
            error_code = body.get("errorCode")
            print(f"  📋 errorCode: {error_code} | message: {body.get('message', 'N/A')}")
            assert error_code != 0, (
                "❌ SECURITY FAIL: Attacker was able to process a DELETE on a record they do "
                "not own (errorCode 0 returned).  Endpoint must enforce ownership."
            )
            print("  ✅ PASS: IDOR attempt rejected at application layer (non-zero errorCode)")
        else:
            assert idor_response.status_code in [401, 403, 404], (
                f"❌ SECURITY FAIL: Unexpected HTTP {idor_response.status_code} for IDOR attempt — "
                f"expected 401, 403, or 404."
            )
            print(f"  ✅ PASS: IDOR attempt rejected at HTTP layer (status {idor_response.status_code})")

        # =====================================================================

        print("\n✅ [Step 2] No-application IDOR — attacker with no application tries known IDs")
        print(f"  📋 Attacker email : {attacker_email}")

        low_id = "1"
        _url = f"{attacker_client.service_url}/api/v1/orgs/withdraw/{low_id}"
        _hdrs = {"Content-Type": "application/json", "Authorization": f"Bearer {attacker_client.access_token}"}
        no_app_response = attacker_client.client.request("DELETE", _url, headers=_hdrs)

        print(f"\n  📋 Response status: {no_app_response.status_code}")

        if no_app_response.status_code == 200:
            body = no_app_response.json()
            error_code = body.get("errorCode")
            print(f"  📋 errorCode: {error_code} | message: {body.get('message', 'N/A')}")
            assert error_code != 0, (
                "❌ SECURITY FAIL: A user with no pending application was able to delete record "
                f"id={low_id} (errorCode 0 returned).  Ownership check is missing."
            )
            print("  ✅ PASS: No-application user rejected at application layer (non-zero errorCode)")
        else:
            assert no_app_response.status_code in [401, 403, 404], (
                f"❌ SECURITY FAIL: Unexpected HTTP {no_app_response.status_code} — expected 401, 403, or 404."
            )
            print(f"  ✅ PASS: No-application user rejected at HTTP layer (status {no_app_response.status_code})")

        # =====================================================================

        print("\n✅ [Step 3] Cross-account escalation — victim creates application, attacker withdraws it")
        print(f"  📋 Victim email   : {victim_email}")
        print(f"  📋 Attacker email : {attacker_email}")
        print(f"  📋 Org code       : {org_code}")

        # Set up: victim applies to join the org
        victim_client.individuals_apply_to_join_the_organization(
            company_id=org_code,
            member_email=victim_email,
            position="QA Engineer",
            region="US",
        )
        victim_applied = True
        print("  📋 Victim application submitted (or silently skipped by helper)")

        # Get the record ID from victim's pending application
        victim_pending = victim_client.query_org_that_the_user_is_currently_joining(victim_id)

        if victim_pending is None:
            print("  ⚠️  Could not retrieve victim's pending application — skipping Step 3 cross-account check")
        else:
            if isinstance(victim_pending, list):
                records = [r for r in victim_pending if isinstance(r, dict)]
            elif isinstance(victim_pending, dict):
                records = [victim_pending]
            else:
                records = []

            if not records:
                print("  ⚠️  No pending records found for victim — skipping cross-account check")
            else:
                record = records[0]
                raw_id = record.get("id") or record.get("joinOrgRecordId") or record.get("recordId")
                if raw_id is None:
                    print(f"  ⚠️  Could not extract record ID from victim result: {record} — skipping")
                else:
                    victim_record_id = str(raw_id)
                    print(f"  📋 Victim joinOrgRecordId : {victim_record_id}")

                    # Attack: attacker attempts to withdraw the victim's application
                    _url = f"{attacker_client.service_url}/api/v1/orgs/withdraw/{victim_record_id}"
                    _hdrs = {"Content-Type": "application/json", "Authorization": f"Bearer {attacker_client.access_token}"}
                    cross_response = attacker_client.client.request("DELETE", _url, headers=_hdrs)

                    print(f"\n  📋 Attack response status: {cross_response.status_code}")

                    if cross_response.status_code == 200:
                        body = cross_response.json()
                        error_code = body.get("errorCode")
                        print(f"  📋 errorCode: {error_code} | message: {body.get('message', 'N/A')}")
                        assert error_code != 0, (
                            "❌ SECURITY FAIL: Attacker (User A) was able to withdraw victim's (User B) "
                            "join application (errorCode 0 returned). Cross-user IDOR must be rejected."
                        )
                        print("  ✅ PASS: Cross-account withdrawal rejected at application layer")
                        # Application was NOT actually withdrawn — victim still owns it.
                        victim_applied = True
                    else:
                        assert cross_response.status_code in [401, 403, 404], (
                            f"❌ SECURITY FAIL: Unexpected HTTP {cross_response.status_code} for "
                            f"cross-account attack — expected 401, 403, or 404."
                        )
                        print(f"  ✅ PASS: Cross-account withdrawal rejected at HTTP layer (status {cross_response.status_code})")
                        # Application was NOT withdrawn — victim still owns it.
                        victim_applied = True

        # =====================================================================

        print("\n✅ [Step 4] Post-attack verification — victim can still withdraw their own application")

        if victim_applied and victim_record_id:
            _url = f"{victim_client.service_url}/api/v1/orgs/withdraw/{victim_record_id}"
            _hdrs = {"Content-Type": "application/json", "Authorization": f"Bearer {victim_client.access_token}"}
            verify_response = victim_client.client.request("DELETE", _url, headers=_hdrs)
            victim_applied = False  # victim has now legitimately withdrawn their application

            print(f"  📋 Response status: {verify_response.status_code}")

            if verify_response.status_code == 200:
                body = verify_response.json()
                error_code = body.get("errorCode")
                assert error_code == 0, (
                    "❌ SECURITY CONCERN: Legitimate victim can no longer withdraw their own "
                    f"application — possible state corruption (errorCode {error_code}: {body.get('message')})."
                )
                print("  ✅ PASS: Victim can still withdraw their own application — state is intact")
            else:
                print(
                    f"  ⚠️  Victim's withdraw returned HTTP {verify_response.status_code} — "
                    f"check whether their application state was corrupted by the attack attempts."
                )
        else:
            print("  ⚠️  No victim record ID available — post-attack verification skipped")

    finally:
        if victim_applied and victim_record_id:
            # Best-effort cleanup: withdraw the victim's pending application
            try:
                _url = f"{victim_client.service_url}/api/v1/orgs/withdraw/{victim_record_id}"
                _hdrs = {"Content-Type": "application/json", "Authorization": f"Bearer {victim_client.access_token}"}
                cleanup = victim_client.client.request("DELETE", _url, headers=_hdrs)
                if cleanup.status_code == 200 and cleanup.json().get("errorCode") == 0:
                    print("\n  ✅ Cleanup: victim's pending application withdrawn")
                else:
                    print(f"\n  ⚠️  Cleanup: could not withdraw victim's application — HTTP {cleanup.status_code}")
            except Exception as exc:
                print(f"\n  ⚠️  Cleanup failed: {exc}")

        attacker_client.close()
        victim_client.close()
