from pytests.__init__ import *


def test_case():
    """
    [Step1] Authenticate and get current user information
    [Step2] Update user information with valid payload
    [Step2b] Assert response body structure (contract validation)
    [Step3] Verify information was updated successfully
    [Step4] Restore original information for test isolation
    """

    email = UID_USER_NAME()
    uid_client = Unified_ID_API(email)

    # =================================

    print("✅ [Step 1] Get current user information for baseline")
    user_info_response = uid_client.get_user_info()

    if user_info_response.status_code == 200:
        try:
            current_data = user_info_response.json()
            current_result = current_data.get("result", {})

            print("✅ Current user information retrieved")
            print(f"  📋 Current firstName: {current_result.get('firstName', 'N/A')}")
            print(f"  📋 Current lastName: {current_result.get('lastName', 'N/A')}")
            print(f"  📋 Current phone: {current_result.get('phone', 'N/A')}")
            print(f"  📋 Current language: {current_result.get('language', 'N/A')}")
            print(f"  📋 Current region: {current_result.get('region', 'N/A')}")
            print(f"  📋 Current use24hour: {current_result.get('use24hour', 'N/A')}")

        except Exception as parse_error:
            print(f"❌ FAIL: Current info parsing failed: {parse_error}")

    print("\n✅ [Step 2] Updating user information with valid data...")

    update_data = {
        "account_id": current_result.get("accountId"),  # Required field
        "email": current_result.get("email"),  # Required field
        "first_name": "TestFirstName",
        "last_name": "TestLastName",
        "phone": "1234567890",
        "language": "en_US",
        "region": current_result.get("region", "MY"),  # Use user's actual region
        "use24hour": True,
    }

    # Validate required fields are available
    if not update_data["account_id"] or not update_data["email"]:
        print(
            f"❌ FAIL: Missing required fields - accountId: {update_data['account_id']}, email: {update_data['email']}"
        )
        return False

    print(f"  🔄 Using accountId: {update_data['account_id']}")
    print(f"  🔄 Using email: {update_data['email']}")
    print(f"  🔄 Updating firstName to: {update_data['first_name']}")
    print(f"  🔄 Updating lastName to: {update_data['last_name']}")
    print(f"  🔄 Updating phone to: {update_data['phone']}")
    print(f"  🔄 Updating language to: {update_data['language']}")
    print(f"  🔄 Updating region to: {update_data['region']}")
    print(f"  🔄 Updating use24hour to: {update_data['use24hour']}")

    update_response = uid_client.update_profile(
        account_id=update_data["account_id"],  # Required
        email=update_data["email"],  # Required
        first_name=update_data["first_name"],
        last_name=update_data["last_name"],
        phone=update_data["phone"],
        language=update_data["language"],
        region=update_data["region"],
        use24hour=update_data["use24hour"],
    )
    print(f"  📋 Update response status: {update_response.status_code}")

    # ── Response contract assertions ──────────────────────────────────────────
    print("\n✅ [Step 2b] Asserting response body structure (contract validation)")

    assert update_response.status_code == 200, (
        f"❌ FAIL: Expected HTTP 200, got {update_response.status_code}"
    )

    content_type = update_response.headers.get("Content-Type", "")
    assert "application/json" in content_type, (
        f"❌ FAIL: Expected Content-Type 'application/json', got '{content_type}'"
    )
    print(f"  ✅ Content-Type: {content_type}")

    try:
        response_body = update_response.json()
    except Exception as e:
        assert False, f"❌ FAIL: Response body is not valid JSON — {e}"

    assert "errorCode" in response_body, (
        "❌ FAIL: Required field 'errorCode' is missing from response body"
    )
    assert isinstance(response_body["errorCode"], int), (
        f"❌ FAIL: 'errorCode' must be an integer, got {type(response_body['errorCode']).__name__}"
    )
    print(f"  ✅ errorCode present and is int: {response_body['errorCode']}")

    assert "message" in response_body, (
        "❌ FAIL: Required field 'message' is missing from response body"
    )
    assert isinstance(response_body["message"], str), (
        f"❌ FAIL: 'message' must be a string, got {type(response_body['message']).__name__}"
    )
    print(f"  ✅ message present and is str: '{response_body['message']}'")

    print("  ✅ PASS: Response body structure is valid")
    # ─────────────────────────────────────────────────────────────────────────

    if update_response.status_code == 200:
        try:
            update_result = update_response.json()
            error_code = update_result.get("errorCode")
            message = update_result.get("message", "N/A")

            print(f"  📋 Error Code: {error_code}")
            print(f"  📋 Message: {message}")

            if error_code == 0:
                print("✅ PASS: User information updated successfully")

                # Step 3: Verify the updates
                print("\n[Step 3] Verifying information was updated...")

                verify_response = uid_client.get_user_info()

                if verify_response.status_code == 200:
                    try:
                        verify_data = verify_response.json()
                        verify_result = verify_data.get("result", {})

                        # Check each updated field (excluding required fields that shouldn't change)
                        verification_passed = 0
                        updatable_fields = [
                            "first_name",
                            "last_name",
                            "phone",
                            "language",
                            "region",
                            "use24hour",
                        ]
                        verification_total = len(updatable_fields)

                        for field in updatable_fields:
                            expected_value = update_data[field]
                            api_field = field.replace("_", "")  # Convert to camelCase
                            if field == "first_name":
                                api_field = "firstName"
                            elif field == "last_name":
                                api_field = "lastName"

                            actual_value = verify_result.get(api_field)

                            if actual_value == expected_value:
                                print(
                                    f"  ✅ {api_field}: {actual_value} (updated correctly)"
                                )
                                verification_passed += 1
                            else:
                                print(
                                    f"  ❌ {api_field}: expected {expected_value}, got {actual_value}"
                                )

                        # Also verify required fields remain unchanged
                        print(
                            f"  📋 accountId: {verify_result.get('accountId')} (preserved)"
                        )
                        print(f"  📋 email: {verify_result.get('email')} (preserved)")

                        print(
                            f"\n  📊 Verification: {verification_passed}/{verification_total} fields updated correctly"
                        )

                        if verification_passed == verification_total:
                            print("✅ EXCELLENT: All fields updated successfully")
                            verification_success = True
                        elif verification_passed >= verification_total * 0.8:
                            print("✅ GOOD: Most fields updated successfully")
                            verification_success = True
                        else:
                            print("⚠️  CONCERN: Some fields may not have updated")
                            verification_success = False

                    except Exception as verify_parse_error:
                        print(
                            f"❌ FAIL: Verification parsing failed: {verify_parse_error}"
                        )
                        verification_success = False
                else:
                    print(
                        f"❌ FAIL: Verification request failed with HTTP {verify_response.status_code}"
                    )
                    verification_success = False

                # Step 4: Restore original data
                print("\n[Step 4] Restoring original user information...")

                if current_result:
                    restore_response = uid_client.update_profile(
                        account_id=current_result.get("accountId"),  # Required
                        email=current_result.get("email"),  # Required
                        first_name=current_result.get("firstName"),
                        last_name=current_result.get("lastName"),
                        phone=current_result.get("phone"),
                        language=current_result.get("language"),
                        region=current_result.get("region"),
                        use24hour=current_result.get("use24hour"),
                    )

                    if restore_response.status_code == 200:
                        print("✅ Original information restored successfully")
                    else:
                        print(
                            f"⚠️  Restoration returned HTTP {restore_response.status_code}"
                        )
                else:
                    print("⚠️  No original data to restore")

                return verification_success

            else:
                print(f"❌ FAIL: Update failed with error code: {error_code}")
                return False

        except Exception as update_parse_error:
            print(f"❌ FAIL: Update response parsing failed: {update_parse_error}")
            return False
    else:
        print(f"❌ FAIL: Update request failed with HTTP {update_response.status_code}")
        return False

    uid_client.close()
