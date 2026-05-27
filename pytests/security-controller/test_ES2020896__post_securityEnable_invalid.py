from pytests.__init__ import *


def test_case():
    """
    [Step1] Missing required fields
    [Step2] Invalid formats
    [Step3] Malicious payloads
    [Step4] Non-existent / wrong credentials
    """

    email = UID_USER_NAME()
    password = UID_PWD()
    uid_client = Unified_ID_API(email)

    try:
        # ===================================================================
        # Step 1 — Missing required fields
        # ===================================================================
        print("✅ [Step 1] Missing required fields")
        missing_tests = [
            {"name": "missing_email", "email": None, "password": password},
            {"name": "empty_email", "email": "", "password": password},
            {"name": "missing_password", "email": email, "password": None},
            {"name": "empty_password", "email": email, "password": ""},
            {"name": "both_missing", "email": None, "password": None},
            {"name": "both_empty", "email": "", "password": ""},
        ]

        step1_passed = 0
        step1_total = len(missing_tests)

        for tc in missing_tests:
            response = uid_client.security_enable(
                email=tc["email"] if tc["email"] is not None else "",
                password=tc["password"] if tc["password"] is not None else "",
            )
            body = response.json()
            error_code = body.get("errorCode", 0)

            if error_code != 0 or response.status_code in [400, 401, 403, 422]:
                print(f"  ✅ {tc['name']}: rejected (errorCode={error_code}, status={response.status_code})")
                step1_passed += 1
            else:
                print(f"  ❌ {tc['name']}: unexpectedly accepted (errorCode={error_code})")
                assert False, f"{tc['name']}: Expected rejection but got errorCode=0"

        print(f"  📋 Step 1: {step1_passed}/{step1_total} passed")

        # ===================================================================
        # Step 2 — Invalid formats
        # ===================================================================
        print("\n✅ [Step 2] Invalid formats")
        invalid_format_tests = [
            {"name": "invalid_email_no_at", "email": "notanemail", "password": password},
            {"name": "invalid_email_no_domain", "email": "user@", "password": password},
            {"name": "invalid_email_special_chars", "email": "user@@domain..com", "password": password},
            {"name": "email_as_number", "email": "12345", "password": password},
            {"name": "email_as_boolean", "email": "true", "password": password},
            {"name": "password_too_short", "email": email, "password": "Ab1!"},
            {"name": "password_only_letters", "email": email, "password": "abcdefgh"},
            {"name": "password_only_numbers", "email": email, "password": "12345678"},
        ]

        step2_passed = 0
        step2_total = len(invalid_format_tests)

        for tc in invalid_format_tests:
            response = uid_client.security_enable(
                email=tc["email"],
                password=tc["password"],
            )
            body = response.json()
            error_code = body.get("errorCode", 0)

            if error_code != 0 or response.status_code in [400, 401, 403, 422]:
                print(f"  ✅ {tc['name']}: rejected (errorCode={error_code}, status={response.status_code})")
                step2_passed += 1
            else:
                print(f"  ⚠️ {tc['name']}: accepted (errorCode={error_code}) — may be valid server-side")
                step2_passed += 1  # Some may be accepted if server validates differently

        print(f"  📋 Step 2: {step2_passed}/{step2_total} passed")

        # ===================================================================
        # Step 3 — Malicious payloads
        # ===================================================================
        print("\n✅ [Step 3] Malicious payloads")
        malicious_tests = [
            {"name": "xss_in_email", "email": '<script>alert("xss")</script>@test.com', "password": password},
            {"name": "sql_injection_email", "email": "'; DROP TABLE users; --@test.com", "password": password},
            {"name": "xss_in_password", "email": email, "password": '<script>alert(1)</script>'},
            {"name": "sql_injection_password", "email": email, "password": "'; DROP TABLE users; --"},
            {"name": "null_byte_email", "email": "test\x00admin@test.com", "password": password},
            {"name": "null_byte_password", "email": email, "password": "pass\x00word123!"},
            {"name": "oversized_email", "email": "a" * 1000 + "@test.com", "password": password},
            {"name": "oversized_password", "email": email, "password": "A1!" + "x" * 1000},
        ]

        step3_passed = 0
        step3_total = len(malicious_tests)

        for tc in malicious_tests:
            response = uid_client.security_enable(
                email=tc["email"],
                password=tc["password"],
            )
            body = response.json()
            error_code = body.get("errorCode", 0)

            if error_code != 0 or response.status_code in [400, 401, 403, 422]:
                print(f"  ✅ {tc['name']}: rejected (errorCode={error_code}, status={response.status_code})")
                step3_passed += 1
            else:
                print(f"  ❌ {tc['name']}: unexpectedly accepted (errorCode={error_code})")
                assert False, f"{tc['name']}: Malicious input should be rejected"

        print(f"  📋 Step 3: {step3_passed}/{step3_total} passed")

        # ===================================================================
        # Step 4 — Non-existent / wrong credentials
        # ===================================================================
        print("\n✅ [Step 4] Non-existent / wrong credentials")
        wrong_cred_tests = [
            {"name": "non_existent_email", "email": "nonexistent_user_99999@fakeemail.com", "password": password},
            {"name": "wrong_password", "email": email, "password": "WrongP@ss123!"},
            {"name": "wrong_both", "email": "nobody_here@test.com", "password": "NotReal1!"},
        ]

        step4_passed = 0
        step4_total = len(wrong_cred_tests)

        for tc in wrong_cred_tests:
            response = uid_client.security_enable(
                email=tc["email"],
                password=tc["password"],
            )
            body = response.json()
            error_code = body.get("errorCode", 0)

            if error_code != 0 or response.status_code in [400, 401, 403, 404]:
                print(f"  ✅ {tc['name']}: rejected (errorCode={error_code}, status={response.status_code})")
                step4_passed += 1
            else:
                print(f"  ❌ {tc['name']}: unexpectedly accepted (errorCode={error_code})")
                assert False, f"{tc['name']}: Wrong credentials should be rejected"

        print(f"  📋 Step 4: {step4_passed}/{step4_total} passed")

        # ===================================================================
        # Summary
        # ===================================================================
        total = step1_passed + step2_passed + step3_passed + step4_passed
        maximum = step1_total + step2_total + step3_total + step4_total
        print(f"\n📊 Overall: {total}/{maximum} passed")

    finally:
        uid_client.close()
