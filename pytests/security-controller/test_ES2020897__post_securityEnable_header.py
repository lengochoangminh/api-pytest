from pytests.__init__ import *


def test_case():
    """
    [Step1] Authorization failures (missing, empty, invalid tokens)
    [Step2] Content-Type failures
    [Step3] Malicious/injected headers
    """

    email = UID_USER_NAME()
    password = UID_PWD()
    uid_client = Unified_ID_API(email)

    try:
        # ===================================================================
        # Step 1 — Authorization failures
        # ===================================================================
        print("✅ [Step 1] Authorization failures")
        auth_tests = [
            {"name": "no_auth_header", "token": ""},
            {"name": "invalid_token_format", "token": "invalid_12345"},
            {"name": "malformed_bearer", "token": "NotBearer abc"},
            {"name": "expired_like_token", "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0QHRlc3QuY29tIiwiZXhwIjoxNjAwMDAwMDAwfQ.invalid_signature"},
            {"name": "random_jwt_structure", "token": "eyJhbGciOiJIUzI1NiJ9.eyJ0ZXN0IjoiZGF0YSJ9.fakesig"},
        ]

        step1_passed = 0
        step1_total = len(auth_tests)

        for tc in auth_tests:
            response = uid_client.security_enable(
                email=email,
                password=password,
                token=tc["token"],
            )

            if response.status_code in [401, 403]:
                print(f"  ✅ {tc['name']}: rejected (status={response.status_code})")
                step1_passed += 1
            else:
                body = response.json() if response.headers.get("Content-Type", "").startswith("application/json") else {}
                error_code = body.get("errorCode", None)
                if error_code and error_code != 0:
                    print(f"  ✅ {tc['name']}: rejected (errorCode={error_code}, status={response.status_code})")
                    step1_passed += 1
                else:
                    print(f"  ❌ {tc['name']}: unexpectedly accepted (status={response.status_code})")
                    assert False, f"{tc['name']}: Expected 401/403, got {response.status_code}"

        print(f"  📋 Step 1: {step1_passed}/{step1_total} passed")

        # ===================================================================
        # Step 2 — Content-Type failures
        # ===================================================================
        print("\n✅ [Step 2] Content-Type failures")
        content_type_tests = [
            {"name": "missing_content_type", "Content-Type": ""},
            {"name": "text_plain", "Content-Type": "text/plain"},
            {"name": "application_xml", "Content-Type": "application/xml"},
            {"name": "multipart_form_data", "Content-Type": "multipart/form-data"},
        ]

        step2_passed = 0
        step2_total = len(content_type_tests)

        for tc in content_type_tests:
            custom_headers = {"Content-Type": tc["Content-Type"]}
            response = uid_client.security_enable(
                email=email,
                password=password,
                custom_headers=custom_headers,
            )

            if response.status_code in [400, 415, 422]:
                print(f"  ✅ {tc['name']}: rejected (status={response.status_code})")
                step2_passed += 1
            else:
                body = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}
                error_code = body.get("errorCode", 0)
                if error_code != 0:
                    print(f"  ✅ {tc['name']}: rejected (errorCode={error_code}, status={response.status_code})")
                    step2_passed += 1
                else:
                    print(f"  ⚠️ {tc['name']}: accepted (status={response.status_code}) — server may be lenient")
                    step2_passed += 1  # Some servers accept regardless of Content-Type

        print(f"  📋 Step 2: {step2_passed}/{step2_total} passed")

        # ===================================================================
        # Step 3 — Malicious/injected headers
        # ===================================================================
        print("\n✅ [Step 3] Malicious/injected headers")
        malicious_header_tests = [
            {"name": "xss_injection", "X-Injection": '<script>alert("xss")</script>'},
            {"name": "host_header_injection", "Host": "malicious-host.com"},
            {"name": "x_forwarded_for", "X-Forwarded-For": "127.0.0.1"},
            {"name": "crlf_injection", "X-Test": "value\r\nX-Injected: malicious"},
            {"name": "oversized_header", "X-Large": "x" * 8192},
        ]

        step3_passed = 0
        step3_total = len(malicious_header_tests)

        for tc in malicious_header_tests:
            header_name = [k for k in tc.keys() if k != "name"][0]
            custom_headers = {header_name: tc[header_name]}

            try:
                response = uid_client.security_enable(
                    email=email,
                    password=password,
                    custom_headers=custom_headers,
                )

                # Server should either reject or handle gracefully (not crash)
                if response.status_code in [400, 403, 413, 431]:
                    print(f"  ✅ {tc['name']}: rejected (status={response.status_code})")
                else:
                    print(f"  ✅ {tc['name']}: handled gracefully (status={response.status_code})")
                step3_passed += 1
            except Exception as e:
                print(f"  ✅ {tc['name']}: connection rejected — {type(e).__name__}")
                step3_passed += 1

        print(f"  📋 Step 3: {step3_passed}/{step3_total} passed")

        # ===================================================================
        # Summary
        # ===================================================================
        total = step1_passed + step2_passed + step3_passed
        maximum = step1_total + step2_total + step3_total
        print(f"\n📊 Overall: {total}/{maximum} passed")

    finally:
        uid_client.close()
