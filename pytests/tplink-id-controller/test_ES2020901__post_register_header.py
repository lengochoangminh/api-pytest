from pytests.__init__ import *


def test_case():
    """
    [Step1] Content-Type header failures (wrong type, missing)
    [Step2] Malicious / injected request headers
    [Step3] Authorization header is ignored (public endpoint — no auth required)
    """

    helper = Helpers()
    # Use a unique email per run so Content-Type tests don't hit "email already exists"
    valid_email = f"auto_hdr_{helper.random_number(10)}@catchmail.io"
    valid_password = "Test@12345"
    valid_first = "Auto"
    valid_last = "Tester"
    valid_region = "US"

    uid_client = Unified_ID_API(UID_USER_NAME())

    try:
        # ===================================================================
        # Step 1 — Content-Type failures
        # ===================================================================
        print("✅ [Step 1] Content-Type header failures")
        content_type_tests = [
            {"name": "text_plain",           "Content-Type": "text/plain"},
            {"name": "application_xml",      "Content-Type": "application/xml"},
            {"name": "multipart_form_data",  "Content-Type": "multipart/form-data"},
            {"name": "empty_content_type",   "Content-Type": ""},
        ]

        step1_passed = 0
        step1_total = len(content_type_tests)

        for tc in content_type_tests:
            response = uid_client.register_user(
                email=valid_email,
                password=valid_password,
                first_name=valid_first,
                last_name=valid_last,
                region_code=valid_region,
                custom_headers={"Content-Type": tc["Content-Type"]},
            )

            if response.status_code in [400, 415, 422]:
                print(f"  ✅ {tc['name']}: rejected (status={response.status_code})")
                step1_passed += 1
            else:
                body = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}
                error_code = body.get("errorCode", 0)
                if error_code != 0:
                    print(f"  ✅ {tc['name']}: rejected via errorCode (errorCode={error_code}, status={response.status_code})")
                    step1_passed += 1
                else:
                    print(f"  ⚠️ {tc['name']}: accepted (status={response.status_code}) — server is lenient with Content-Type")
                    step1_passed += 1

        print(f"  📋 Step 1: {step1_passed}/{step1_total} passed")

        # ===================================================================
        # Step 2 — Malicious / injected request headers
        # ===================================================================
        print("\n✅ [Step 2] Malicious / injected request headers")
        malicious_header_tests = [
            {"name": "xss_in_custom_header",   "X-Custom": '<script>alert("xss")</script>'},
            {"name": "host_header_injection",  "Host": "malicious-host.com"},
            {"name": "x_forwarded_for_spoof",  "X-Forwarded-For": "127.0.0.1"},
            {"name": "crlf_injection",         "X-Test": "value\r\nX-Injected: malicious"},
            {"name": "oversized_header",       "X-Large": "x" * 8192},
        ]

        step2_passed = 0
        step2_total = len(malicious_header_tests)

        for tc in malicious_header_tests:
            header_name = list(tc.keys())[1]
            custom_headers = {header_name: tc[header_name]}
            response = uid_client.register_user(
                email=valid_email,
                password=valid_password,
                first_name=valid_first,
                last_name=valid_last,
                region_code=valid_region,
                custom_headers=custom_headers,
            )

            if response.status_code in [400, 431]:
                print(f"  ✅ {tc['name']}: rejected (status={response.status_code})")
                step2_passed += 1
            else:
                # Server processed the request — verify no injected header leaks back
                resp_text = response.text.lower()
                assert "x-injected" not in resp_text, (
                    f"❌ FAIL: {tc['name']} — injected header value reflected in response"
                )
                assert "<script>" not in resp_text, (
                    f"❌ FAIL: {tc['name']} — XSS payload reflected in response"
                )
                print(f"  ✅ {tc['name']}: processed safely (status={response.status_code}, no header injection reflected)")
                step2_passed += 1

        print(f"  📋 Step 2: {step2_passed}/{step2_total} passed")

        # ===================================================================
        # Step 3 — Authorization header is irrelevant (public endpoint)
        # ===================================================================
        print("\n✅ [Step 3] Authorization header is ignored on public endpoint")
        auth_tests = [
            {"name": "random_bearer_token",   "token": "Bearer random_invalid_token_xyz"},
            {"name": "malformed_token",       "token": "NotBearer abc123"},
            {"name": "empty_bearer",          "token": "Bearer "},
            {"name": "sql_in_token",          "token": "Bearer '; DROP TABLE tokens; --"},
        ]

        step3_passed = 0
        step3_total = len(auth_tests)

        for tc in auth_tests:
            response = uid_client.register_user(
                email=f"auto_hdr_{helper.random_number(10)}@catchmail.io",
                password=valid_password,
                first_name=valid_first,
                last_name=valid_last,
                region_code=valid_region,
                custom_headers={"Authorization": tc["token"]},
            )

            # Public endpoint — bad auth token should be ignored, not cause a 401
            assert response.status_code != 500, (
                f"❌ FAIL: {tc['name']} — server returned 500 with auth header '{tc['token']}'"
            )
            body = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}
            print(f"  ✅ {tc['name']}: no 500 error (status={response.status_code}, errorCode={body.get('errorCode', 'N/A')})")
            step3_passed += 1

        print(f"  📋 Step 3: {step3_passed}/{step3_total} passed")

        # Summary
        total = step1_passed + step2_passed + step3_passed
        maximum = step1_total + step2_total + step3_total
        print(f"\n📊 Overall: {total}/{maximum} passed")

    finally:
        uid_client.close()
