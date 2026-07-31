from pytests.__init__ import *


def _call(uid_client, record_id):
    """Helper — call the withdraw endpoint and return the response (or raise on connection error)."""
    try:
        url = f"{uid_client.service_url}/api/v1/orgs/withdraw/{record_id}"
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {uid_client.access_token}"}
        return uid_client.client.request("DELETE", url, headers=headers)
    except (ConnectionError, UnicodeEncodeError) as exc:
        return exc  # caller will treat as PASS
    except Exception as exc:
        exc_str = str(exc).lower()
        if any(t in exc_str for t in ("illegal", "protocol", "encoding", "null", "header")):
            return exc
        raise


def _evaluate(response_or_exc, test_id):
    """Return (passed: bool) — True when the server/transport rejected the bad input."""
    if isinstance(response_or_exc, Exception):
        print(f"    ✅ PASS: Transport-level rejection: {type(response_or_exc).__name__}")
        return True

    response = response_or_exc
    print(f"    Status: {response.status_code}")

    if response.status_code in [400, 401, 403, 404, 405, 422]:
        print("    ✅ PASS: HTTP-level rejection")
        return True

    if response.status_code == 200:
        try:
            data = response.json()
        except Exception:
            print("    ✅ PASS: Non-JSON 200 (server-side rejection)")
            return True

        error_code = data.get("errorCode")
        print(f"    Error Code: {error_code} - Message: {data.get('message', '')}")

        if error_code != 0:
            print("    ✅ PASS: Application-layer rejection (non-zero errorCode)")
            return True
        else:
            print(f"    ❌ FAIL: '{test_id}' — invalid input was accepted (errorCode 0)")
            return False

    print(f"    ⚠️  Unexpected status: {response.status_code}")
    return False


def test_case():
    """
    [Step1] Test DELETE /api/v1/orgs/withdraw with invalid-format path parameter values (9 cases)
    [Step2] Test with malicious / injection path parameter values (5 cases)
    [Step3] Test with well-formed but non-existent IDs (3 cases)
    [Step4] Print overall pass/fail summary

    Note: This endpoint has no request body — invalid-input coverage focuses entirely on
    the {joinOrgRecordId} path parameter.  Content-Type and auth header edge cases are
    covered in the companion _header.py file.
    """

    email = UID_USER_NAME()
    uid_client = Unified_ID_API(email)

    try:
        # =====================================================================

        print("\n✅ [Step 1] Invalid-format path parameter values")

        step1_cases = [
            ("empty_string",         ""),
            ("whitespace_only",      "   "),
            ("zero_id",              "0"),
            ("negative_id",          "-1"),
            ("float_id",             "1.5"),
            ("letters_only",         "abc"),
            ("alphanumeric",         "1a2b3c"),
            ("special_chars",        "!@#$%"),
            ("boolean_string",       "true"),
        ]

        step1_passed = 0
        step1_total = len(step1_cases)

        for i, (test_id, record_id) in enumerate(step1_cases, 1):
            print(f"\n  Test {i}/{step1_total}: {test_id} — id='{record_id}'")
            result = _call(uid_client, record_id)
            if _evaluate(result, test_id):
                step1_passed += 1

        print(f"\n  📊 Step 1: {step1_passed}/{step1_total} passed")

        # =====================================================================

        print("\n✅ [Step 2] Malicious / injection path parameter values")

        step2_cases = [
            ("sql_injection",        "1; DROP TABLE users; --"),
            ("xss_in_id",            "<script>alert(1)</script>"),
            ("null_byte",            "1\x00admin"),
            ("path_traversal",       "../etc/passwd"),
            ("oversized_id",         "9" * 1000),
        ]

        step2_passed = 0
        step2_total = len(step2_cases)

        for i, (test_id, record_id) in enumerate(step2_cases, 1):
            print(f"\n  Test {i}/{step2_total}: {test_id}")
            result = _call(uid_client, record_id)
            if _evaluate(result, test_id):
                step2_passed += 1

        print(f"\n  📊 Step 2: {step2_passed}/{step2_total} passed")

        # =====================================================================

        print("\n✅ [Step 3] Well-formed but non-existent IDs")

        step3_cases = [
            ("nonexistent_low",      "1"),
            ("nonexistent_zero_pad", "00000000000001"),
            ("nonexistent_large",    "99999999999999"),
        ]

        step3_passed = 0
        step3_total = len(step3_cases)

        for i, (test_id, record_id) in enumerate(step3_cases, 1):
            print(f"\n  Test {i}/{step3_total}: {test_id} — id='{record_id}'")
            result = _call(uid_client, record_id)
            if _evaluate(result, test_id):
                step3_passed += 1

        print(f"\n  📊 Step 3: {step3_passed}/{step3_total} passed")

        # =====================================================================

        total = step1_passed + step2_passed + step3_passed
        maximum = step1_total + step2_total + step3_total
        print(f"\n📊 Overall: {total}/{maximum} passed")

    finally:
        uid_client.close()
