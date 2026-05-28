from pytests.__init__ import *


def test_case():
    """
    [Step1] Call POST /api/v1/register with all required fields and a unique catchmail.io email
    [Step2] Assert response contract (HTTP 200, Content-Type, errorCode int, message str)
    [Step3] Assert business logic — errorCode == 0, registration accepted
    """

    helper = Helpers()
    test_email = f"auto_register_{helper.random_number(10)}@catchmail.io"
    password = "Test@12345"
    first_name = "Auto"
    last_name = "Tester"
    region_code = "US"

    uid_client = Unified_ID_API(UID_USER_NAME())

    try:
        print("✅ [Step 1] Call POST /api/v1/register with valid required fields")
        print(f"  📋 Email: {test_email}")
        print(f"  📋 RegionCode: {region_code}")

        response = uid_client.register_user(
            email=test_email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            region_code=region_code,
            subscription=False,
            terminal_uuid=Helpers.generate_UUID(),
        )
        print(f"  📋 Response status: {response.status_code}")

        # ── Response contract ──────────────────────────────────────────────
        print("\n✅ [Step 2] Assert response contract")

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

        # ── Business logic ─────────────────────────────────────────────────
        print("\n✅ [Step 3] Assert registration was accepted")

        assert body["errorCode"] == 0, (
            f"❌ FAIL: Registration failed — errorCode {body['errorCode']}: {body.get('message')}"
        )
        print(f"  📋 Registered email: {test_email}")
        print("  ✅ PASS: errorCode == 0, registration accepted successfully")

    finally:
        uid_client.close()
