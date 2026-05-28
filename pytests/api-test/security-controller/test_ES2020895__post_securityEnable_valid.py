from pytests.__init__ import *


def test_case():
    """
    [Step1] Authenticate as primary test user
    [Step2] Call POST /api/v1/security/enable with valid email and password
    [Step2b] Assert response contract (HTTP 200, Content-Type, errorCode, message)
    [Step3] Verify securityToken is returned in the result
    """

    email = UID_USER_NAME()
    password = UID_PWD()
    uid_client = Unified_ID_API(email)

    try:
        print("✅ [Step 1] Authenticate as primary test user")
        print(f"  📋 Email: {email}")

        print("\n✅ [Step 2] Call POST /api/v1/security/enable with valid payload")
        response = uid_client.security_enable(
            email=email,
            password=password,
        )
        print(f"  📋 Response status: {response.status_code}")

        print("\n✅ [Step 2b] Assert response contract")
        assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"

        content_type = response.headers.get("Content-Type", "")
        assert "application/json" in content_type, f"Expected application/json, got '{content_type}'"

        try:
            body = response.json()
        except Exception as e:
            assert False, f"Response body is not valid JSON — {e}"

        assert "errorCode" in body, "Required field 'errorCode' missing from response body"
        assert isinstance(body["errorCode"], int), f"'errorCode' must be int, got {type(body['errorCode']).__name__}"
        assert "message" in body, "Required field 'message' missing from response body"
        assert isinstance(body["message"], str), f"'message' must be str, got {type(body['message']).__name__}"
        print(f"  ✅ errorCode: {body['errorCode']} | message: '{body['message']}'")

        assert body["errorCode"] == 0, f"Expected errorCode 0, got {body['errorCode']} — {body.get('message')}"
        print("  ✅ PASS: Endpoint returned errorCode 0")

        print("\n✅ [Step 3] Verify securityToken is returned")
        result = body.get("result", {})
        assert result is not None, "Expected 'result' field in response body"
        security_token = result.get("securityToken")
        assert security_token is not None, "Expected 'securityToken' in result"
        assert isinstance(security_token, str), f"'securityToken' must be str, got {type(security_token).__name__}"
        assert len(security_token) > 0, "Expected non-empty securityToken"
        print(f"  📋 securityToken length: {len(security_token)}")
        print("  ✅ PASS: securityToken is present and non-empty")

    finally:
        uid_client.close()
