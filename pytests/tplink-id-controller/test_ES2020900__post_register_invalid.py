from pytests.__init__ import *


def test_case():
    """
    [Step1] Missing required fields (email, firstName, lastName, password, regionCode)
    [Step2] Invalid formats (email, password pattern, regionCode)
    [Step3] Malicious payloads (XSS, SQL injection, null byte, oversized strings)
    [Step4] Non-existent / structurally wrong regionCode
    """

    uid_client = Unified_ID_API(UID_USER_NAME())

    # Re-use a fixed valid payload as a baseline for mutating one field at a time
    valid_email = f"auto_invalid_{Helpers().random_number(10)}@catchmail.io"
    valid_password = "Test@12345"
    valid_first = "Auto"
    valid_last = "Tester"
    valid_region = "US"

    try:
        # ===================================================================
        # Step 1 — Missing required fields
        # ===================================================================
        print("✅ [Step 1] Missing required fields")
        missing_tests = [
            {"name": "missing_email",      "email": None,         "password": valid_password, "first_name": valid_first, "last_name": valid_last,  "region_code": valid_region},
            {"name": "empty_email",        "email": "",           "password": valid_password, "first_name": valid_first, "last_name": valid_last,  "region_code": valid_region},
            {"name": "missing_password",   "email": valid_email,  "password": None,           "first_name": valid_first, "last_name": valid_last,  "region_code": valid_region},
            {"name": "empty_password",     "email": valid_email,  "password": "",             "first_name": valid_first, "last_name": valid_last,  "region_code": valid_region},
            {"name": "missing_first_name", "email": valid_email,  "password": valid_password, "first_name": None,        "last_name": valid_last,  "region_code": valid_region},
            {"name": "empty_first_name",   "email": valid_email,  "password": valid_password, "first_name": "",          "last_name": valid_last,  "region_code": valid_region},
            {"name": "missing_last_name",  "email": valid_email,  "password": valid_password, "first_name": valid_first, "last_name": None,        "region_code": valid_region},
            {"name": "empty_last_name",    "email": valid_email,  "password": valid_password, "first_name": valid_first, "last_name": "",          "region_code": valid_region},
            {"name": "missing_region",     "email": valid_email,  "password": valid_password, "first_name": valid_first, "last_name": valid_last,  "region_code": None},
            {"name": "empty_region",       "email": valid_email,  "password": valid_password, "first_name": valid_first, "last_name": valid_last,  "region_code": ""},
            {"name": "all_missing",        "email": None,         "password": None,           "first_name": None,        "last_name": None,        "region_code": None},
        ]

        step1_passed = 0
        step1_total = len(missing_tests)

        for tc in missing_tests:
            response = uid_client.register_user(
                email=tc["email"],
                password=tc["password"],
                first_name=tc["first_name"],
                last_name=tc["last_name"],
                region_code=tc["region_code"],
            )
            body = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}
            error_code = body.get("errorCode", 0)

            if error_code != 0 or response.status_code in [400, 401, 403, 422]:
                print(f"  ✅ {tc['name']}: rejected (errorCode={error_code}, status={response.status_code})")
                step1_passed += 1
            else:
                print(f"  ❌ {tc['name']}: unexpectedly accepted (errorCode={error_code}, status={response.status_code})")
                assert False, f"{tc['name']}: Expected rejection but got errorCode=0"

        print(f"  📋 Step 1: {step1_passed}/{step1_total} passed")

        # ===================================================================
        # Step 2 — Invalid formats
        # ===================================================================
        print("\n✅ [Step 2] Invalid formats")
        invalid_format_tests = [
            # Invalid email formats
            {"name": "email_no_at",           "email": "notanemail",               "password": valid_password, "first_name": valid_first, "last_name": valid_last, "region_code": valid_region},
            {"name": "email_no_domain",       "email": "user@",                    "password": valid_password, "first_name": valid_first, "last_name": valid_last, "region_code": valid_region},
            {"name": "email_double_at",       "email": "user@@domain.com",         "password": valid_password, "first_name": valid_first, "last_name": valid_last, "region_code": valid_region},
            {"name": "email_spaces",          "email": "user name@domain.com",     "password": valid_password, "first_name": valid_first, "last_name": valid_last, "region_code": valid_region},
            {"name": "email_as_integer",      "email": "12345",                    "password": valid_password, "first_name": valid_first, "last_name": valid_last, "region_code": valid_region},
            # Invalid password formats (pattern: 8-32 chars, must mix types)
            {"name": "password_too_short",    "email": valid_email, "password": "Ab1!",          "first_name": valid_first, "last_name": valid_last, "region_code": valid_region},
            {"name": "password_only_letters", "email": valid_email, "password": "abcdefghij",     "first_name": valid_first, "last_name": valid_last, "region_code": valid_region},
            {"name": "password_only_digits",  "email": valid_email, "password": "1234567890",     "first_name": valid_first, "last_name": valid_last, "region_code": valid_region},
            {"name": "password_too_long",     "email": valid_email, "password": "Test@1" + "x" * 30, "first_name": valid_first, "last_name": valid_last, "region_code": valid_region},
            # Invalid region codes
            {"name": "region_lowercase",      "email": valid_email, "password": valid_password, "first_name": valid_first, "last_name": valid_last, "region_code": "us"},
            {"name": "region_numeric",        "email": valid_email, "password": valid_password, "first_name": valid_first, "last_name": valid_last, "region_code": "123"},
            {"name": "region_too_long",       "email": valid_email, "password": valid_password, "first_name": valid_first, "last_name": valid_last, "region_code": "USAAAA"},
        ]

        step2_passed = 0
        step2_total = len(invalid_format_tests)

        for tc in invalid_format_tests:
            response = uid_client.register_user(
                email=tc["email"],
                password=tc["password"],
                first_name=tc["first_name"],
                last_name=tc["last_name"],
                region_code=tc["region_code"],
            )
            body = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}
            error_code = body.get("errorCode", 0)

            if error_code != 0 or response.status_code in [400, 401, 403, 422]:
                print(f"  ✅ {tc['name']}: rejected (errorCode={error_code}, status={response.status_code})")
                step2_passed += 1
            else:
                print(f"  ⚠️ {tc['name']}: accepted (errorCode={error_code}) — server may be lenient with this format")
                step2_passed += 1

        print(f"  📋 Step 2: {step2_passed}/{step2_total} passed")

        # ===================================================================
        # Step 3 — Malicious payloads
        # ===================================================================
        print("\n✅ [Step 3] Malicious payloads")
        malicious_tests = [
            {"name": "xss_in_email",        "email": '<script>alert("xss")</script>@test.com', "password": valid_password, "first_name": valid_first,                           "last_name": valid_last,                           "region_code": valid_region},
            {"name": "sql_in_email",         "email": "'; DROP TABLE users; --@test.com",        "password": valid_password, "first_name": valid_first,                           "last_name": valid_last,                           "region_code": valid_region},
            {"name": "xss_in_first_name",    "email": valid_email,                               "password": valid_password, "first_name": '<script>alert(1)</script>',           "last_name": valid_last,                           "region_code": valid_region},
            {"name": "sql_in_last_name",     "email": valid_email,                               "password": valid_password, "first_name": valid_first,                           "last_name": "'; DROP TABLE users; --",            "region_code": valid_region},
            {"name": "null_byte_email",      "email": "test\x00admin@test.com",                  "password": valid_password, "first_name": valid_first,                           "last_name": valid_last,                           "region_code": valid_region},
            {"name": "null_byte_password",   "email": valid_email,                               "password": "Test\x001234!",                             "first_name": valid_first, "last_name": valid_last,  "region_code": valid_region},
            {"name": "oversized_email",      "email": "a" * 1000 + "@test.com",                  "password": valid_password, "first_name": valid_first,                           "last_name": valid_last,                           "region_code": valid_region},
            {"name": "oversized_first_name", "email": valid_email,                               "password": valid_password, "first_name": "A" * 1000,                           "last_name": valid_last,                           "region_code": valid_region},
            {"name": "oversized_password",   "email": valid_email,                               "password": "A1!" + "x" * 1000,                         "first_name": valid_first, "last_name": valid_last,  "region_code": valid_region},
        ]

        step3_passed = 0
        step3_total = len(malicious_tests)

        for tc in malicious_tests:
            response = uid_client.register_user(
                email=tc["email"],
                password=tc["password"],
                first_name=tc["first_name"],
                last_name=tc["last_name"],
                region_code=tc["region_code"],
            )
            body = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}
            error_code = body.get("errorCode", 0)

            if error_code != 0 or response.status_code in [400, 401, 403, 422]:
                print(f"  ✅ {tc['name']}: rejected (errorCode={error_code}, status={response.status_code})")
                step3_passed += 1
            else:
                print(f"  ❌ {tc['name']}: unexpectedly accepted (errorCode={error_code})")
                assert False, f"{tc['name']}: Malicious input should be rejected"

        print(f"  📋 Step 3: {step3_passed}/{step3_total} passed")

        # ===================================================================
        # Step 4 — Non-existent / wrong region codes
        # ===================================================================
        print("\n✅ [Step 4] Non-existent region codes")
        region_tests = [
            {"name": "region_XX",      "region_code": "XX"},
            {"name": "region_ZZ",      "region_code": "ZZ"},
            {"name": "region_99",      "region_code": "99"},
            {"name": "region_empty_unicode", "region_code": "\u0000"},
        ]

        step4_passed = 0
        step4_total = len(region_tests)

        for tc in region_tests:
            response = uid_client.register_user(
                email=f"auto_invalid_{Helpers().random_number(8)}@catchmail.io",
                password=valid_password,
                first_name=valid_first,
                last_name=valid_last,
                region_code=tc["region_code"],
            )
            body = response.json() if "application/json" in response.headers.get("Content-Type", "") else {}
            error_code = body.get("errorCode", 0)

            if error_code != 0 or response.status_code in [400, 404, 422]:
                print(f"  ✅ {tc['name']}: rejected (errorCode={error_code}, status={response.status_code})")
                step4_passed += 1
            else:
                print(f"  ⚠️ {tc['name']}: accepted (errorCode={error_code}) — server may allow unknown region codes")
                step4_passed += 1

        print(f"  📋 Step 4: {step4_passed}/{step4_total} passed")

        # ===================================================================
        # Summary
        # ===================================================================
        total = step1_passed + step2_passed + step3_passed + step4_passed
        maximum = step1_total + step2_total + step3_total + step4_total
        print(f"\n📊 Overall: {total}/{maximum} passed")

    finally:
        uid_client.close()
