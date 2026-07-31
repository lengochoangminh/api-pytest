from pytests.__init__ import *


def test_case():
    """
    [Step1] Apply to join the cert org to create a pending application (setup)
    [Step2] Query pending application to obtain the joinOrgRecordId
    [Step3] Call DELETE /api/v1/orgs/withdraw/{joinOrgRecordId} with a valid ID
    [Step3b] Assert response contract (HTTP status, Content-Type, errorCode, message)
    [Step4] Assert business logic — errorCode == 0 (application successfully withdrawn)

    Pre-condition: UID_USER_NAME must NOT currently be a member of CERT_COMPANY_ID.
    Post-condition: The created join application is withdrawn — state is clean.
    """

    email = UID_USER_NAME()
    account_id = UID_ACCOUNT_ID()
    org_code = CERT_COMPANY_ID()

    uid_client = Unified_ID_API(email)

    applied = False
    join_record_id = None

    try:
        # =================================

        print("✅ [Step 1] Apply to join the org (setup — creates a pending application)")
        print(f"  📋 Applicant email : {email}")
        print(f"  📋 Org code        : {org_code}")

        uid_client.individuals_apply_to_join_the_organization(
            company_id=org_code,
            member_email=email,
            position="QA Engineer",
            region="US",
        )
        applied = True
        print("  ✅ Application submitted (or silently skipped by the existing helper)")

        # =================================

        print("\n✅ [Step 2] Query pending application to get joinOrgRecordId")

        pending_result = uid_client.query_org_that_the_user_is_currently_joining(account_id)

        assert pending_result is not None, (
            "❌ FAIL: query_org_that_the_user_is_currently_joining returned None — "
            "verify the account ID is correct and the application was created."
        )
        print(f"  📋 Raw pending result: {pending_result}")

        if isinstance(pending_result, list):
            records = [r for r in pending_result if isinstance(r, dict)]
        elif isinstance(pending_result, dict):
            records = [pending_result]
        else:
            records = []

        assert records, (
            "❌ FAIL: No pending application records found after submitting the application."
        )

        record = records[0]
        raw_id = record.get("id") or record.get("joinOrgRecordId") or record.get("recordId")
        assert raw_id is not None, (
            f"❌ FAIL: Could not extract joinOrgRecordId — record keys: {list(record.keys())}"
        )
        join_record_id = str(raw_id)
        print(f"  📋 joinOrgRecordId : {join_record_id}")

        # =================================

        print(f"\n✅ [Step 3] Call DELETE /api/v1/orgs/withdraw/{join_record_id}")

        _url = f"{uid_client.service_url}/api/v1/orgs/withdraw/{join_record_id}"
        _hdrs = {"Content-Type": "application/json", "Authorization": f"Bearer {uid_client.access_token}"}
        response = uid_client.client.request("DELETE", _url, headers=_hdrs)
        applied = False  # application has been removed by the DELETE call

        print(f"  📋 Response status: {response.status_code}")

        # =================================

        print("\n✅ [Step 3b] Assert response contract")

        assert response.status_code == 200, (
            f"❌ FAIL: Expected HTTP 200, got {response.status_code}"
        )

        content_type = response.headers.get("Content-Type", "")
        assert "application/json" in content_type, (
            f"❌ FAIL: Expected Content-Type 'application/json', got '{content_type}'"
        )
        print(f"  ✅ Content-Type: {content_type}")

        try:
            body = response.json()
        except Exception as e:
            assert False, f"❌ FAIL: Response body is not valid JSON — {e}"

        assert "errorCode" in body, "❌ FAIL: Required field 'errorCode' missing from response body"
        assert isinstance(body["errorCode"], int), (
            f"❌ FAIL: 'errorCode' must be int, got {type(body['errorCode']).__name__}"
        )
        assert "message" in body, "❌ FAIL: Required field 'message' missing from response body"
        assert isinstance(body["message"], str), (
            f"❌ FAIL: 'message' must be str, got {type(body['message']).__name__}"
        )
        print(f"  ✅ errorCode: {body['errorCode']} | message: '{body['message']}'")
        print("  ✅ PASS: Response contract is valid")

        # =================================

        print("\n✅ [Step 4] Assert business logic — withdrawal accepted")

        assert body["errorCode"] == 0, (
            f"❌ FAIL: Withdrawal rejected — errorCode {body['errorCode']}: {body.get('message')}"
        )
        print("  ✅ PASS: Organization join application successfully withdrawn")

    finally:
        if applied and join_record_id:
            # The main test did not reach the DELETE call — clean up the pending application.
            print("\n⚠️  Cleanup: test failed before withdraw — attempting to remove pending application")
            try:
                _url = f"{uid_client.service_url}/api/v1/orgs/withdraw/{join_record_id}"
                _hdrs = {"Content-Type": "application/json", "Authorization": f"Bearer {uid_client.access_token}"}
                cleanup = uid_client.client.request("DELETE", _url, headers=_hdrs)
                if cleanup.status_code == 200 and cleanup.json().get("errorCode") == 0:
                    print("  ✅ Cleanup: pending application removed")
                else:
                    print(f"  ⚠️  Cleanup: unexpected response HTTP {cleanup.status_code}")
            except Exception as exc:
                print(f"  ⚠️  Cleanup failed: {exc}")

        uid_client.close()
