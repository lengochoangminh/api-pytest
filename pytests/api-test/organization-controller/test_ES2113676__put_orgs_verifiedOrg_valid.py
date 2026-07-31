from pytests.__init__ import *


def test_case():
    """
    [Step1] Get baseline — capture the current verified org name for restore
    [Step2] Call PUT /api/v1/orgs/verifiedOrg with a valid payload
    [Step2b] Assert response contract (HTTP status, Content-Type, errorCode, message)
    [Step3] Assert business logic — errorCode == 0
    [Step4] Restore original org name (always runs in finally)    
    """

    owner_email = ORG_OWNER_EMAIL()
    org_code = CERT_COMPANY_ID()
    original_name = CERT_COMPANY_NAME()
    new_name = "Auto_VerifiedOrg_Test"

    uid_client = Unified_ID_API(owner_email)

    try:
        # =================================

        print("✅ [Step 1] Get baseline")
        print(f"  📋 Owner email: {owner_email}")
        print(f"  📋 Org code: {org_code}")
        print(f"  📋 Original name (from config): {original_name}")

        # =================================

        print("\n✅ [Step 2] Call PUT /api/v1/orgs/verifiedOrg with valid payload")

        response = uid_client.verify_org(
            org_code=org_code,
            name=new_name,
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

        print("\n✅ [Step 3] Assert business logic — update accepted")

        assert body["errorCode"] == 0, (
            f"❌ FAIL: Update rejected — errorCode {body['errorCode']}: {body.get('message')}"
        )
        print("  ✅ PASS: Verified org updated successfully")

        # NOTE: Verify persistence (re-fetching org info after update) requires a
        # GET /api/v1/orgs/{orgCode} endpoint — add when that method is available.

    finally:
        # =================================

        print("\n✅ [Step 4] Restore original org name")

        try:
            restore_response = uid_client.verify_org(
                org_code=org_code,
                name=original_name,
            )
            if restore_response.status_code == 200:
                restore_body = restore_response.json()
                if restore_body.get("errorCode") == 0:
                    print(f"  ✅ PASS: Org name restored to '{original_name}'")
                else:
                    print(
                        f"  ⚠️  Restore call returned errorCode {restore_body.get('errorCode')}: {restore_body.get('message')}"
                    )
            else:
                print(f"  ⚠️  Restore call returned HTTP {restore_response.status_code}")
        except Exception as restore_error:
            print(f"  ⚠️  Restore call failed: {restore_error}")
        finally:
            uid_client.close()
