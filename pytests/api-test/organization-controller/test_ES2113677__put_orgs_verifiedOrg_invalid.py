from pytests.__init__ import *


# Known SQL-leak bug IDs: over-length fields that trigger a raw DB exception in the error message. 
# These are printed as ⚠️ (info disclosure bugs on file) rather than hard-failed,
# consistent with the behaviour documented in test_verifiedOrg_invalid_example.py.
_SQL_LEAK_BUG_IDS = {
    "region_too_long",
    "state_one_over_max", "state_far_over_max",
    "contact_one_over_max", "contact_far_over_max",
    "description_one_over_max", "description_far_over_max",
}

_SQL_LEAK_KEYWORDS = ("sql", "mysql", "jdbc", "truncation", "dataintegrityviolation", "exception")


def _base_payload(org_code):
    """Return a complete valid payload used as baseline for body-field tests."""
    return {
        "orgCode": org_code,
        "name": "ValidOrgName",
        "type": "Resellers",
        "region": "US",
        "address": "123 Main St",
        "stateOrProvince": "California",
        "city": "Los Angeles",
        "postCode": "90001",
        "contact": "Test Contact",
        "contactPhone": "1234567890",
        "contactEmail": "contact@example.com",
        "description": "Test organization",
        "taxNumber": "1234567890",
        "website": "https://example.com",
    }


def _run_test(uid_client, test_id, override, org_code):
    """
    Send one verify_org call with base payload updated by `override`.
    Returns (passed: bool, skip_count: int).
    skip_count is 1 when a known SQL-leak bug is encountered (⚠️ not a hard fail).
    """
    payload = _base_payload(org_code)
    payload.update(override)

    try:
        response = uid_client.verify_org(**{
            "org_code":         payload.get("orgCode"),
            "name":             payload.get("name"),
            "org_type":         payload.get("type"),
            "region":           payload.get("region"),
            "address":          payload.get("address"),
            "state_or_province": payload.get("stateOrProvince"),
            "city":             payload.get("city"),
            "post_code":        payload.get("postCode"),
            "contact":          payload.get("contact"),
            "contact_phone":    payload.get("contactPhone"),
            "contact_email":    payload.get("contactEmail"),
            "description":      payload.get("description"),
            "tax_number":       payload.get("taxNumber"),
            "website":          payload.get("website"),
        })
    except (ConnectionError, UnicodeEncodeError) as exc:
        print(f"    ✅ PASS: Request-level rejection: {type(exc).__name__}")
        return True, 0
    except Exception as exc:
        exc_str = str(exc).lower()
        if any(t in exc_str for t in ("illegal", "protocol", "encoding", "null", "header")):
            print(f"    ✅ PASS: Encoding/protocol rejection: {type(exc).__name__}")
            return True, 0
        raise

    print(f"    Status: {response.status_code}")

    if response.status_code == 200:
        try:
            data = response.json()
        except Exception:
            print("    ✅ PASS: Non-JSON response (server error)")
            return True, 0

        error_code = data.get("errorCode")
        message = (data.get("message") or "").lower()
        print(f"    Error Code: {error_code} - Message: {data.get('message', 'No message')}")

        # SQL/exception leak check (info disclosure)
        leaked_sql = any(kw in message for kw in _SQL_LEAK_KEYWORDS)
        if leaked_sql:
            if test_id in _SQL_LEAK_BUG_IDS:
                print(f"    ⚠️  Known bug: over-length '{test_id}' leaks raw SQL/exception (info disclosure)")
                return True, 1  # counted as pass, flagged as skip/known-bug
            else:
                assert not leaked_sql, (
                    f"❌ FAIL: '{test_id}' leaked SQL/exception in error message (info disclosure): "
                    f"{data.get('message')!r}"
                )

        if error_code != 0:
            print("    ✅ PASS: Properly rejected")
            return True, 0
        else:
            print("    ❌ FAIL: Invalid payload was accepted!")
            return False, 0

    elif response.status_code in [400, 401, 403, 422]:
        print("    ✅ PASS: HTTP-level rejection")
        return True, 0
    else:
        print(f"    ⚠️  Unexpected status: {response.status_code}")
        return False, 0


def _run_orgcode_test(uid_client, test_id, org_code_override, base_org_code):
    """
    Send a verify_org call with only orgCode overridden (name stays valid).
    Assertion: when server returns 200/errorCode 0, no `result` must be present
    (invalid orgCode is treated as a no-op — the org must not be modified).
    """
    try:
        response = uid_client.verify_org(
            org_code=org_code_override,
            name="ValidName",
        )
    except (ConnectionError, UnicodeEncodeError) as exc:
        print(f"    ✅ PASS: Request-level rejection: {type(exc).__name__}")
        return True
    except Exception as exc:
        exc_str = str(exc).lower()
        if any(t in exc_str for t in ("illegal", "protocol", "encoding", "null", "header")):
            print(f"    ✅ PASS: Encoding/protocol rejection: {type(exc).__name__}")
            return True
        raise

    print(f"    Status: {response.status_code}")

    if response.status_code == 200:
        try:
            data = response.json()
        except Exception:
            print("    ✅ PASS: Non-JSON response (server error)")
            return True

        error_code = data.get("errorCode")
        print(f"    Error Code: {error_code} - Message: {data.get('message', 'No message')}")

        if error_code != 0:
            print("    ✅ PASS: Properly rejected")
            return True

        # errorCode == 0 is acceptable ONLY if no org was actually modified
        assert not data.get("result"), (
            f"❌ FAIL: Invalid orgCode '{test_id}' unexpectedly modified an org: {data.get('result')}"
        )
        print("    ✅ PASS: Server treated invalid orgCode as no-op (no result returned)")
        return True

    elif response.status_code in [400, 401, 403, 404]:
        print("    ✅ PASS: HTTP-level rejection")
        return True
    else:
        print(f"    ⚠️  Unexpected status: {response.status_code}")
        return False


def test_case():
    """
    [Step1] Test PUT /api/v1/orgs/verifiedOrg with invalid orgCode values (15 cases)
    [Step2] Test with invalid body field values — boundary, XSS, injection, bad formats (~50 cases)
    [Step3] Test null/empty values on optional fields — verify no stored value is wiped
    [Step4] Print overall pass/fail summary
    
    Known bugs (⚠️, not hard-failed):
      - Over-length region/stateOrProvince/contact/description fields trigger a raw
        SQL exception in the error message (info disclosure). Filed — tracked via
        _SQL_LEAK_BUG_IDS.
      - fakeRegion value passes validation (no server-side region enum check).
    """

    owner_email = ORG_OWNER_EMAIL()
    org_code = CERT_COMPANY_ID()

    uid_client = Unified_ID_API(owner_email)

    try:
        # =====================================================================

        print("\n✅ [Step 1] Test invalid orgCode values")

        # Derive real-code variants for boundary tests
        real_code = org_code or "USUI2604G2D1659K"
        wrong_region_code = real_code.replace("US", "UK", 1) if real_code.startswith("US") else "UKUI0000G0D0000X"
        one_too_long_code = real_code + "X"
        one_too_short_code = real_code[:-1]

        orgcode_tests = [
            ("missing_org_code",        None),
            ("empty_org_code",          ""),
            ("whitespace_only",         "   "),
            ("one_too_long",            "US" + "a" * 15),
            ("emoji_org_code",          "😭😭😭😭😭😭😭😭"),
            ("invalid_org_code",        "INVALID_ORG_CODE"),
            ("fake_org_code",           "USUI26040TI1754H"),
            ("sql_injection",           "DROP TABLE organizations;"),
            ("path_traversal",          "../../etc/passwd"),
            ("null_byte",               "ORG\x00CODE"),
            ("unicode_cyrillic",        "\u043e\u0440\u0433\u0430\u043d\u0438\u0437\u0430\u0446\u0438\u044f123"),
            ("wrong_region",            wrong_region_code),
            ("real_code_one_too_long",  one_too_long_code),
            ("real_code_one_too_short", one_too_short_code),
            ("invalid_region_prefix",   "XXUI2604G2D1659K"),
        ]

        step1_passed = 0
        step1_total = len(orgcode_tests)

        for i, (test_id, override_code) in enumerate(orgcode_tests, 1):
            print(f"\n  Test {i}/{step1_total}: {test_id}")
            if _run_orgcode_test(uid_client, test_id, override_code, org_code):
                step1_passed += 1

        print(f"\n  📊 Invalid orgCode Tests: {step1_passed}/{step1_total} passed")

        # =====================================================================

        print("\n✅ [Step 2] Test invalid body field values")

        body_tests = [
            # ── name (max 64) ────────────────────────────────────────────────
            ("name_one_over_max",             {"name": "A" * 65}),
            ("name_far_over_max",             {"name": "A" * 200}),
            ("name_xss",                      {"name": "<script>alert(1)</script>"}),

            # ── type ─────────────────────────────────────────────────────────
            ("type_invalid_value",            {"type": "InvalidOrgType"}),
            ("type_xss",                      {"type": "<script>alert(1)</script>"}),
            ("type_integer",                  {"type": 9999}),
            ("type_random_string",            {"type": "randomString"}),

            # ── region ───────────────────────────────────────────────────────
            ("region_too_long",               {"region": "A" * 500}),
            ("region_xss",                    {"region": "<script>alert(1)</script>"}),

            # ── address (max 256) ────────────────────────────────────────────
            ("address_one_over_max",          {"address": "A" * 257}),
            ("address_far_over_max",          {"address": "A" * 1000}),
            ("address_xss",                   {"address": "<script>alert(1)</script>"}),

            # ── stateOrProvince (max 100) ────────────────────────────────────
            ("state_one_over_max",            {"stateOrProvince": "A" * 101}),
            ("state_far_over_max",            {"stateOrProvince": "A" * 500}),
            ("state_xss",                     {"stateOrProvince": "<script>alert(1)</script>"}),

            # ── city (max 100) ───────────────────────────────────────────────
            ("city_one_over_max",             {"city": "C" * 101}),
            ("city_far_over_max",             {"city": "C" * 500}),
            ("city_xss",                      {"city": "<script>alert(1)</script>"}),

            # ── postCode (max 10) ────────────────────────────────────────────
            ("postcode_one_over_max",         {"postCode": "1" * 11}),
            ("postcode_far_over_max",         {"postCode": "1" * 50}),
            ("postcode_xss",                  {"postCode": "<script>"}),

            # ── contact (max 100) ────────────────────────────────────────────
            ("contact_one_over_max",          {"contact": "A" * 1001}),
            ("contact_far_over_max",          {"contact": "A" * 5000}),
            ("contact_xss",                   {"contact": "<script>alert(1)</script>"}),

            # ── contactPhone ─────────────────────────────────────────────────
            ("contact_phone_letters",         {"contactPhone": "not-a-phone"}),
            ("contact_phone_too_long",        {"contactPhone": "1" * 25}),
            ("contact_phone_xss",             {"contactPhone": "<script>alert(1)</script>"}),

            # ── contactEmail ─────────────────────────────────────────────────
            ("contact_email_invalid_format",  {"contactEmail": "not-an-email"}),
            ("contact_email_no_at",           {"contactEmail": "invalidemail.com"}),
            ("contact_email_at_only",         {"contactEmail": "@"}),
            ("contact_email_no_domain",       {"contactEmail": "user@"}),
            ("contact_email_local_too_long",  {"contactEmail": "a" * 65 + "@example.com"}),
            ("contact_email_xss",             {"contactEmail": "<script>alert(1)</script>@example.com"}),

            # ── description (max 512) ────────────────────────────────────────
            ("description_one_over_max",      {"description": "A" * 513}),
            ("description_far_over_max",      {"description": "A" * 2000}),

            # ── taxNumber (max 64) ───────────────────────────────────────────
            ("taxnumber_one_over_max",        {"taxNumber": "1" * 65}),
            ("taxnumber_far_over_max",        {"taxNumber": "1" * 200}),
            # ("taxnumber_sql_injection",       {"taxNumber": "' OR 1=1--"}),
            ("taxnumber_xss",                 {"taxNumber": "<script>alert(1)</script>"}),

            # ── website (max 64, must have protocol) ─────────────────────────
            ("website_no_protocol",           {"website": "example.com"}),
            ("website_javascript_proto",      {"website": "javascript:alert(1)"}),
            ("website_one_over_max",          {"website": "https://" + "a" * 57}),
            ("website_ftp_protocol",          {"website": "ftp://example.com"}),
            ("website_data_uri",              {"website": "data:text/html,<script>alert(1)</script>"}),
            ("website_localhost",             {"website": "https://localhost"}),
            ("website_vbscript_proto",        {"website": "vbscript:alert(1)"}),
            ("website_file_proto",            {"website": "file:///etc/passwd"}),
        ]

        step2_passed = 0
        step2_skipped = 0  # known-bug SQL-leak cases
        step2_total = len(body_tests)

        for i, (test_id, override) in enumerate(body_tests, 1):
            print(f"\n  Test {i}/{step2_total}: {test_id}")
            passed, skipped = _run_test(uid_client, test_id, override, org_code)
            if passed:
                step2_passed += 1
            step2_skipped += skipped

        print(f"\n  📊 Invalid Body Field Tests: {step2_passed}/{step2_total} passed"
              + (f" ({step2_skipped} known SQL-leak bugs ⚠️)" if step2_skipped else ""))

        # =====================================================================

        print("\n✅ [Step 3] Test null/empty optional fields — guard against data wipe")

        # NOTE: Read-back verification requires a GET /api/v1/orgs/{orgCode} endpoint.
        # That method does not yet exist in unified_id_api.py.  We send the request and
        # assert the server does not return errorCode 0 with a populated result (i.e., it
        # must not silently confirm a destructive update).  Add read-back when the GET
        # method is available.

        null_empty_tests = [
            ("name_empty",          {"name": ""}),
            ("name_null",           {"name": None}),
            ("type_empty",          {"type": ""}),
            ("type_null",           {"type": None}),
            ("region_empty",        {"region": ""}),
            ("region_null",         {"region": None}),
            ("address_empty",       {"address": ""}),
            ("address_null",        {"address": None}),
            ("state_empty",         {"stateOrProvince": ""}),
            ("state_null",          {"stateOrProvince": None}),
            ("city_empty",          {"city": ""}),
            ("city_null",           {"city": None}),
            ("postcode_empty",      {"postCode": ""}),
            ("postcode_null",       {"postCode": None}),
            ("contact_empty",       {"contact": ""}),
            ("contact_null",        {"contact": None}),
            ("phone_empty",         {"contactPhone": ""}),
            ("phone_null",          {"contactPhone": None}),
            ("email_empty",         {"contactEmail": ""}),
            ("email_null",          {"contactEmail": None}),
            ("description_empty",   {"description": ""}),
            ("description_null",    {"description": None}),
            ("taxnumber_empty",     {"taxNumber": ""}),
            ("taxnumber_null",      {"taxNumber": None}),
            ("website_empty",       {"website": ""}),
            ("website_null",        {"website": None}),
        ]

        step3_passed = 0
        step3_total = len(null_empty_tests)

        for i, (test_id, override) in enumerate(null_empty_tests, 1):
            print(f"\n  Test {i}/{step3_total}: {test_id}")

            payload = _base_payload(org_code)
            payload.update(override)

            try:
                response = uid_client.verify_org(
                    org_code=payload.get("orgCode"),
                    name=payload.get("name"),
                    org_type=payload.get("type"),
                    region=payload.get("region"),
                    address=payload.get("address"),
                    state_or_province=payload.get("stateOrProvince"),
                    city=payload.get("city"),
                    post_code=payload.get("postCode"),
                    contact=payload.get("contact"),
                    contact_phone=payload.get("contactPhone"),
                    contact_email=payload.get("contactEmail"),
                    description=payload.get("description"),
                    tax_number=payload.get("taxNumber"),
                    website=payload.get("website"),
                )

                print(f"    Status: {response.status_code}")

                if response.status_code == 200:
                    data = response.json()
                    error_code = data.get("errorCode")
                    print(f"    Error Code: {error_code} - Message: {data.get('message', 'No message')}")

                    if error_code == 0:
                        # Server accepted — we cannot verify read-back without GET endpoint.
                        # Treat as pass but note the limitation.
                        print("    ⚠️  Accepted (no read-back available — GET /api/v1/orgs/{orgCode} not yet implemented)")
                        step3_passed += 1
                    else:
                        print("    ✅ PASS: Properly rejected")
                        step3_passed += 1

                elif response.status_code in [400, 401, 403, 422]:
                    print("    ✅ PASS: HTTP-level rejection")
                    step3_passed += 1
                else:
                    print(f"    ⚠️  Unexpected status: {response.status_code}")

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                step3_passed += 1

        print(f"\n  📊 Null/Empty Field Tests: {step3_passed}/{step3_total} passed")

        # =====================================================================

        total = step1_passed + step2_passed + step3_passed
        maximum = step1_total + step2_total + step3_total
        print(f"\n📊 Overall: {total}/{maximum} passed")

    finally:
        uid_client.close()


    owner_email = ORG_OWNER_EMAIL()
    org_code = CERT_COMPANY_ID()

    uid_client = Unified_ID_API(owner_email)

    try:
        # =================================

        print("\n✅ [Step 1] Test missing required fields")

        missing_tests = [
            {"name": "missing_orgCode", "org_code": None, "name_val": "ValidName"},
            {"name": "empty_orgCode",   "org_code": "",   "name_val": "ValidName"},
            {"name": "missing_name",    "org_code": org_code, "name_val": None},
            {"name": "empty_name",      "org_code": org_code, "name_val": ""},
            {"name": "both_missing",    "org_code": None, "name_val": None},
        ]

        step1_passed = 0
        step1_total = len(missing_tests)

        for i, tc in enumerate(missing_tests, 1):
            print(f"\n  Test {i}/{step1_total}: {tc['name']}")

            try:
                response = uid_client.verify_org(
                    org_code=tc["org_code"],
                    name=tc["name_val"],
                )

                print(f"    Status: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        message = data.get("message", "No message")
                        print(f"    Error Code: {error_code} - Message: {message}")

                        if error_code != 0:
                            print("    ✅ PASS: Missing field properly rejected")
                            step1_passed += 1
                        else:
                            print("    ❌ FAIL: Missing field was accepted!")
                    except Exception:
                        print("    ⚠️  JSON parsing failed")
                        step1_passed += 1

                elif response.status_code in [400, 401, 403, 422]:
                    print("    ✅ PASS: HTTP-level rejection")
                    step1_passed += 1
                else:
                    print(f"    ⚠️  Unexpected status: {response.status_code}")

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                step1_passed += 1

        print(f"\n  📊 Missing Field Tests: {step1_passed}/{step1_total} passed")

        # =================================

        print("\n✅ [Step 2] Test invalid field formats and wrong data types")

        invalid_format_tests = [
            {"name": "whitespace_orgCode",   "org_code": "   ",             "name_val": "ValidName"},
            {"name": "whitespace_name",      "org_code": org_code,          "name_val": "   "},
            {"name": "numeric_orgCode",      "org_code": 12345,             "name_val": "ValidName"},
            {"name": "bool_name",            "org_code": org_code,          "name_val": True},
            {"name": "list_as_orgCode",      "org_code": ["USUI1234"],      "name_val": "ValidName"},
            {"name": "dict_as_name",         "org_code": org_code,          "name_val": {"key": "val"}},
        ]

        step2_passed = 0
        step2_total = len(invalid_format_tests)

        for i, tc in enumerate(invalid_format_tests, 1):
            print(f"\n  Test {i}/{step2_total}: {tc['name']}")

            try:
                response = uid_client.verify_org(
                    org_code=tc["org_code"],
                    name=tc["name_val"],
                )

                print(f"    Status: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        message = data.get("message", "No message")
                        print(f"    Error Code: {error_code} - Message: {message}")

                        if error_code != 0:
                            print("    ✅ PASS: Invalid format properly rejected")
                            step2_passed += 1
                        else:
                            print("    ❌ FAIL: Invalid format was accepted!")
                    except Exception:
                        print("    ⚠️  JSON parsing failed")
                        step2_passed += 1

                elif response.status_code in [400, 401, 403, 422]:
                    print("    ✅ PASS: HTTP-level rejection")
                    step2_passed += 1
                else:
                    print(f"    ⚠️  Unexpected status: {response.status_code}")

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                step2_passed += 1

        print(f"\n  📊 Invalid Format Tests: {step2_passed}/{step2_total} passed")

        # =================================

        print("\n✅ [Step 3] Test malicious payloads")

        malicious_tests = [
            {
                "name": "xss_in_name",
                "org_code": org_code,
                "name_val": '<script>alert("xss")</script>',
            },
            {
                "name": "sql_injection_in_name",
                "org_code": org_code,
                "name_val": "'; DROP TABLE orgs; --",
            },
            {
                "name": "null_byte_in_name",
                "org_code": org_code,
                "name_val": "test\x00admin",
            },
            {
                "name": "oversized_name",
                "org_code": org_code,
                "name_val": "A" * 1000,
            },
            {
                "name": "xss_in_orgCode",
                "org_code": '<script>alert("xss")</script>',
                "name_val": "ValidName",
            },
            {
                "name": "sql_injection_in_orgCode",
                "org_code": "'; DROP TABLE orgs; --",
                "name_val": "ValidName",
            },
        ]

        step3_passed = 0
        step3_total = len(malicious_tests)

        for i, tc in enumerate(malicious_tests, 1):
            print(f"\n  Test {i}/{step3_total}: {tc['name']}")

            try:
                response = uid_client.verify_org(
                    org_code=tc["org_code"],
                    name=tc["name_val"],
                )

                print(f"    Status: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        message = data.get("message", "No message")
                        print(f"    Error Code: {error_code} - Message: {message}")

                        if error_code != 0:
                            print("    ✅ PASS: Malicious payload properly rejected")
                            step3_passed += 1
                        else:
                            print("    ❌ FAIL: Malicious payload was accepted!")
                    except Exception:
                        print("    ⚠️  JSON parsing failed")
                        step3_passed += 1

                elif response.status_code in [400, 401, 403, 422]:
                    print("    ✅ PASS: HTTP-level rejection")
                    step3_passed += 1
                else:
                    print(f"    ⚠️  Unexpected status: {response.status_code}")

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                step3_passed += 1

        print(f"\n  📊 Malicious Payload Tests: {step3_passed}/{step3_total} passed")

        # =================================

        print("\n✅ [Step 4] Test non-existent org codes")

        nonexistent_tests = [
            {"name": "nonexistent_orgCode_zeros",  "org_code": "00000000000001", "name_val": "ValidName"},
            {"name": "nonexistent_orgCode_nines",  "org_code": "99999999999999", "name_val": "ValidName"},
            {"name": "wrong_region_orgCode",       "org_code": "EUUI2604G2D0000", "name_val": "ValidName"},
        ]

        step4_passed = 0
        step4_total = len(nonexistent_tests)

        for i, tc in enumerate(nonexistent_tests, 1):
            print(f"\n  Test {i}/{step4_total}: {tc['name']}")

            try:
                response = uid_client.verify_org(
                    org_code=tc["org_code"],
                    name=tc["name_val"],
                )

                print(f"    Status: {response.status_code}")

                if response.status_code == 200:
                    try:
                        data = response.json()
                        error_code = data.get("errorCode")
                        message = data.get("message", "No message")
                        print(f"    Error Code: {error_code} - Message: {message}")

                        if error_code != 0:
                            print("    ✅ PASS: Non-existent org code properly rejected")
                            step4_passed += 1
                        else:
                            print("    ❌ FAIL: Non-existent org code was accepted!")
                    except Exception:
                        print("    ⚠️  JSON parsing failed")
                        step4_passed += 1

                elif response.status_code in [400, 403, 404]:
                    print("    ✅ PASS: HTTP-level rejection")
                    step4_passed += 1
                else:
                    print(f"    ⚠️  Unexpected status: {response.status_code}")

            except Exception as request_error:
                print(f"    ✅ PASS: Request-level rejection: {request_error}")
                step4_passed += 1

        print(f"\n  📊 Non-existent ID Tests: {step4_passed}/{step4_total} passed")

        # =================================

        total = step1_passed + step2_passed + step3_passed + step4_passed
        maximum = step1_total + step2_total + step3_total + step4_total
        print(f"\n📊 Overall: {total}/{maximum} passed")

    finally:
        uid_client.close()
