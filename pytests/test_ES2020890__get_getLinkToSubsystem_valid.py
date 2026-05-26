from pytests.__init__ import *


def test_case():
    """
    [Step1] Authenticate and call GET /api/v1/get-link-to-subsystem with a valid clientId
    [Step2] Verify the response status code is 200 and errorCode is 0
    [Step3] Verify the response result contains a non-empty redirect link
    """

    email = UID_USER_NAME()
    uid_client = Unified_ID_API(email)

    # =================================

    print("✅ [Step 1] Call GET /api/v1/get-link-to-subsystem with clientId=omada-cloud-portal")
    response = uid_client.get_link_to_subsystem(client_id="omada-cloud-portal")

    print(f"  📋 Response status: {response.status_code}")
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    # =================================

    print("\n✅ [Step 2] Verify errorCode is 0")
    data = response.json()
    print(f"  📋 Response body: {data}")

    error_code = data.get("errorCode")
    assert error_code == 0, f"Expected errorCode 0, got {error_code} — message: {data.get('message')}"

    # =================================

    print("\n✅ [Step 3] Verify result contains subsystem name and homeUrl")
    result = data.get("result", {})

    subsystem_name = result.get("name")
    home_url = result.get("homeUrl")

    assert subsystem_name, f"Expected a non-empty 'name' in result, got: {result}"
    assert home_url, f"Expected a non-empty 'homeUrl' in result, got: {result}"

    print(f"  📋 Subsystem name: {subsystem_name}")
    print(f"  📋 Home URL: {home_url}")

    # =================================

    uid_client.close()
