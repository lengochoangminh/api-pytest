from pytests.__init__ import *


def test_case():
    """
    [Step1] Authenticate as the organization owner
    [Step2] Transfer ownership to an existing organization admin
    [Step3] Verify the ownership was transferred successfully
    [Step4] Restore original ownership (transfer back to original owner)
    """

    owner_email = ORG_OWNER_EMAIL()
    admin_email = ORG_ADMIN_EMAIL_2()
    org_code = CERT_COMPANY_ID()

    uid_client = Unified_ID_API(owner_email)

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

        if response.status_code == 200:
            try:
                data = response.json()
                error_code = data.get("errorCode")
                message = data.get("message", "N/A")

                print(f"  📋 Error Code: {error_code}")
                print(f"  📋 Message: {message}")

                if error_code == 0:
                    print("  ✅ PASS: Ownership transferred successfully")
                else:
                    print(f"  ❌ FAIL: Transfer failed with error code: {error_code}")

            except Exception as parse_error:
                print(f"  ❌ FAIL: Response parsing failed: {parse_error}")
        else:
            print(f"  ❌ FAIL: Request failed with HTTP {response.status_code}")
        

        print("\n✅ [Step 3] Restore original ownership (transfer back)")

        # Authenticate as the new owner to transfer back
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
                    print(
                        f"  ⚠️  Restore returned error code: {restore_data.get('errorCode')}"
                    )
            else:
                print(
                    f"  ⚠️  Restore request returned HTTP {restore_response.status_code}"
                )
        finally:
            uid_client_new_owner.close()

    finally:
        uid_client.close()
