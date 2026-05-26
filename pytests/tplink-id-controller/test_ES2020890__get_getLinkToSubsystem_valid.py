from pytests.__init__ import *


def test_case():
    """
    [Step1] Authenticate and call GET /api/v1/get-link-to-subsystem with a valid clientId
    [Step2] Assert response contract (HTTP status, Content-Type, errorCode type, message type)
    [Step3] Verify errorCode is 0 and result contains subsystem name and homeUrl
    """

    email = UID_USER_NAME()
    uid_client = Unified_ID_API(email)

    try:
        print("✅ [Step 1] Call GET /api/v1/get-link-to-subsystem with clientId=omada-cloud-portal")
        response = uid_client.get_link_to_subsystem(client_id="omada-cloud-portal")

        print(f"  📋 Response status: {response.status_code}")

        # =================================

        print("\n✅ [Step 2] Assert response contract")
        assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"

        content_type = response.headers.get("Content-Type", "")
        assert "application/json" in content_type, (
            f"Expected Content-Type 'application/json', got '{content_type}'"
        )
        print(f"  ✅ Content-Type: {content_type}")

        try:
            body = response.json()
        except Exception as e:
            assert False, f"Response body is not valid JSON — {e}"

        assert "errorCode" in body, "Required field 'errorCode' missing from response body"
        assert isinstance(body["errorCode"], int), (
            f"'errorCode' must be int, got {type(body['errorCode']).__name__}"
        )
        assert "message" in body, "Required field 'message' missing from response body"
        assert isinstance(body["message"], str), (
            f"'message' must be str, got {type(body['message']).__name__}"
        )
        print(f"  ✅ errorCode: {body['errorCode']} | message: '{body['message']}'")
        print("  ✅ PASS: Response contract is valid")

        # =================================

        print("\n✅ [Step 3] Verify errorCode is 0 and result fields")
        assert body["errorCode"] == 0, (
            f"Expected errorCode 0, got {body['errorCode']} — message: {body.get('message')}"
        )

        result = body.get("result", {})
        subsystem_name = result.get("name")
        home_url = result.get("homeUrl")

        assert subsystem_name, f"Expected a non-empty 'name' in result, got: {result}"
        assert home_url, f"Expected a non-empty 'homeUrl' in result, got: {result}"

        print(f"  📋 Subsystem name: {subsystem_name}")
        print(f"  📋 Home URL: {home_url}")
        print("  ✅ PASS: Result fields are valid")

    finally:
        uid_client.close()
