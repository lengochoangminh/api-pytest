from pytests.__init__ import *


def test_case():
    """
    [Step1] Test GET /api/v1/get-link-to-subsystem with missing clientId parameter
    [Step2] Test with an empty clientId value
    [Step3] Test with an unknown/unsupported clientId value
    [Step4] Test with malicious payloads in clientId (XSS, SQL injection, overflow)
    """

    email = UID_USER_NAME()
    uid_client = Unified_ID_API(email)

    # =================================

    print("[Step 1] Testing missing clientId parameter...")
    response = uid_client.get_link_to_subsystem(client_id=None)
    print(f"  📋 Response status: {response.status_code}")

    data = response.json()
    error_code = data.get("errorCode")

    if error_code != 0 or response.status_code in [400, 401, 403, 404, 422]:
        print("  ✅ PASS: Missing clientId properly rejected")
    else:
        print(f"  ❌ FAIL: Missing clientId was accepted — errorCode: {error_code}")

    # =================================

    print("\n[Step 2] Testing empty clientId value...")
    empty_client_id_tests = [
        {"name": "empty_string", "client_id": ""},
        {"name": "whitespace_only", "client_id": "   "},
    ]

    empty_passed = 0
    for i, tc in enumerate(empty_client_id_tests, 1):
        print(f"\n  Test {i}/{len(empty_client_id_tests)}: {tc['name']}")
        response = uid_client.get_link_to_subsystem(client_id=tc["client_id"])
        print(f"    Status: {response.status_code}")

        data = response.json()
        error_code = data.get("errorCode")

        if error_code != 0 or response.status_code in [400, 401, 403, 404, 422]:
            print("    ✅ PASS: Empty clientId properly rejected")
            empty_passed += 1
        else:
            print(f"    ❌ FAIL: Empty clientId was accepted — errorCode: {error_code}")

    print(f"\n  📊 Empty clientId Tests: {empty_passed}/{len(empty_client_id_tests)} passed")

    # =================================

    print("\n[Step 3] Testing unknown/unsupported clientId values...")
    unknown_client_id_tests = [
        {"name": "random_string", "client_id": "unknown-client-xyz"},
        {"name": "nonexistent_subsystem", "client_id": "fake-subsystem-12345"},
        {"name": "numeric_only", "client_id": "123456"},
    ]

    unknown_passed = 0
    for i, tc in enumerate(unknown_client_id_tests, 1):
        print(f"\n  Test {i}/{len(unknown_client_id_tests)}: {tc['name']}")
        response = uid_client.get_link_to_subsystem(client_id=tc["client_id"])
        print(f"    Status: {response.status_code}")

        data = response.json()
        error_code = data.get("errorCode")

        if error_code != 0 or response.status_code in [400, 401, 403, 404, 422]:
            print("    ✅ PASS: Unknown clientId properly rejected")
            unknown_passed += 1
        else:
            print(f"    ❌ FAIL: Unknown clientId was accepted — errorCode: {error_code}")

    print(f"\n  📊 Unknown clientId Tests: {unknown_passed}/{len(unknown_client_id_tests)} passed")

    # =================================

    print("\n[Step 4] Testing malicious payloads in clientId...")
    malicious_tests = [
        {"name": "xss_script_tag", "client_id": '<script>alert("xss")</script>'},
        {"name": "sql_injection", "client_id": "'; DROP TABLE clients; --"},
        {"name": "null_byte_injection", "client_id": "omada\x00admin"},
        {"name": "long_string_overflow", "client_id": "A" * 1000},
        # {"name": "path_traversal", "client_id": "../../etc/passwd"},
    ]

    malicious_passed = 0
    for i, tc in enumerate(malicious_tests, 1):
        print(f"\n  Test {i}/{len(malicious_tests)}: {tc['name']}")
        response = uid_client.get_link_to_subsystem(client_id=tc["client_id"])
        print(f"    Status: {response.status_code}")

        data = response.json()
        error_code = data.get("errorCode")

        if error_code != 0 or response.status_code in [400, 401, 403, 404, 422]:
            print("    ✅ PASS: Malicious payload properly rejected")
            malicious_passed += 1
        else:
            print(f"    ❌ FAIL: Malicious payload was accepted — errorCode: {error_code}")

    print(f"\n  📊 Malicious Payload Tests: {malicious_passed}/{len(malicious_tests)} passed")

    # =================================

    uid_client.close()
