from pytests.__init__ import *


def test_case():
    """
    [Step1] Authenticate as the organization owner
    [Step2] Transfer ownership to an existing organization admin
    [Step2b] Assert response contract (HTTP status, Content-Type, errorCode, message)
    [Step3] Assert business logic — errorCode == 0, ownership transferred
    [Step4] Restore original ownership (transfer back) — always runs in finally
    """

    owner_email = ORG_OWNER_EMAIL()
    admin_email = ORG_ADMIN_EMAIL_2()
    org_code = CERT_COMPANY_ID()

    uid_client = Unified_ID_API(owner_email)
    ownership_transferred = False

    try:
        # =================================

        print("✅ [Step 1] Authenticated as the organization owner")
        print(f"  📋 Owner email: {owner_email}")
        print(f"  📋 Organization code: {org_code}")
        print(f"  📋 New owner email: {admin_email}")

        # =================================

        print("\n✅ [Step 2] Transfer ownership to an existing organization admin")

        response = uid_client.change_org_owner(
            org_code=org_code,
            email=admin_email,
        )

        print(f"  📋 Response status: {response.status_code}")

        # =================================

        print("\n✅ [Step 2b] Assert response contract")

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

        print("\n✅ [Step 3] Assert ownership was transferred successfully")

        assert body["errorCode"] == 0, (
            f"❌ FAIL: Transfer failed — errorCode {body['errorCode']}: {body.get('message')}"
        )
        ownership_transferred = True
        print("  ✅ PASS: Ownership transferred successfully")

        # NOTE: Verify persistence (re-fetching org owner after transfer) requires a
        # GET /api/v1/orgs/{orgCode} endpoint — add when that method is available.

    finally:
        if ownership_transferred:
            print("\n✅ [Step 4] Restoring original ownership (transfer back)")
            uid_client_new_owner = Unified_ID_API(admin_email)
            try:
                restore_response = uid_client_new_owner.change_org_owner(
                    org_code=org_code,
                    email=owner_email,
                )
                print(f"  📋 Restore response status: {restore_response.status_code}")
                if restore_response.status_code == 200:
                    restore_data = restore_response.json()
                    if restore_data.get("errorCode") == 0:
                        print("  ✅ Original ownership restored successfully")
                    else:
                        print(f"  ⚠️  Restore returned errorCode: {restore_data.get('errorCode')}")
                else:
                    print(f"  ⚠️  Restore request returned HTTP {restore_response.status_code}")
            finally:
                uid_client_new_owner.close()

        uid_client.close()
