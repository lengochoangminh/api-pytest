---
applyTo: "pytests/**"
---

# API Test Script Generation — Project Conventions

> **Skills available**:
> - `api-coverage-workflow` (`.github/skills/api-coverage-workflow/SKILL.md`) — fetch Swagger spec, compute coverage gaps, display numbered uncovered list, let the user select one/some/ALL, then generate.
> - `api-pytest-generation` (`.github/skills/api-pytest-generation/SKILL.md`) — generate the full test suite for a single known endpoint.

When the user provides an API endpoint (Swagger spec, curl example, or description), generate a full set of test scripts following every rule in this file exactly.

---

## 1. File Naming Convention

Each endpoint gets **four test files**, one per category. Place them in the folder that matches the Swagger tag (controller name):

```
pytests/{controller-folder}/test_{TICKET}__{http_method}_{endpoint_name}_{category}.py
```

| # | Category | Suffix | Purpose |
|---|----------|--------|---------|
| 1 | Happy path | `_valid.py` | Successful calls, contract validation, field verification |
| 2 | Invalid payload | `_invalid.py` | Missing fields, bad formats, malicious input, non-existent IDs |
| 3 | Header validation | `_header.py` | Auth failures, wrong Content-Type, malicious headers |
| 4 | Wrong HTTP method | `_invalid_method.py` | GET/PUT/DELETE/PATCH/HEAD/OPTIONS against a POST endpoint (or vice versa) |
| 5 *(optional)* | Security / AuthZ | `_security.py` | IDOR, cross-account access, token vs payload identity mismatch — create whenever the endpoint accepts an identity field (`accountId`, `userId`, `email`) |

**Ticket numbers** are sequential from the last ticket used in that folder. Check existing files before assigning.

**Examples for `POST /api/v1/account/updateInfo` (tickets ES1455067–ES1455071):**
```
pytests/user-center-controller/test_ES1455067__post_updateInfo_valid.py
pytests/user-center-controller/test_ES1455068__post_updateInfo_invalid.py
pytests/user-center-controller/test_ES1455069__post_updateInfo_header.py
pytests/user-center-controller/test_ES1455070__post_updateInfo_invalid_method.py
pytests/user-center-controller/test_ES1455071__post_updateInfo_security.py   ← file 5: IDOR + identity mismatch
```

The security file is ticket **+4** from the base ticket (ES1455067 + 4 = ES1455071). **Check for conflicts first** — if +4 is already taken by another endpoint's files, use the next available ticket number beyond +4 and note the deviation in the docstring.

---

## 2. File Structure Template

Every test file starts with this exact import and a single test function:

```python
from pytests.__init__ import *


def test_case():
    """
    [Step1] <description>
    [Step2] <description>
    ...
    """

    email = UID_USER_NAME()
    uid_client = Unified_ID_API(email)

    try:
        # test steps here
        pass
    finally:
        uid_client.close()
```

**Rules:**
- Import is always `from pytests.__init__ import *` — nothing else.
- Test function is always named `test_case()` with no parameters.
- Wrap all steps in `try/finally` so `uid_client.close()` always runs.
- If the test modifies shared data (e.g., updates a profile), restore the original in the `finally` block.

---

## 3. Available Config Symbols

These are imported via `pytests/__init__.py` and ready to use without further import:

| Symbol | Type | Description |
|--------|------|-------------|
| `UID_USER_NAME()` | str | Primary test user email (User A) |
| `UID_ACCOUNT_ID()` | str | Primary test user accountId (User A) |
| `UID_PWD()` | str | Shared test password |
| `ORG_MEMBER_EMAIL()` | str | Secondary user email (User B) — use for IDOR / cross-account tests |
| `ORG_MEMBER_ACCOUNT_ID()` | str | Secondary user accountId (User B) |
| `ORG_OWNER_EMAIL()` | str | Organization owner email |
| `ORG_OWNER_ACCOUNT_ID()` | str | Organization owner accountId |
| `ORG_ADMIN_EMAIL()` | str | Organization admin email |
| `ORG_ADMIN_EMAIL_2()` | str | Second organization admin email |
| `CERT_COMPANY_ID()` | str | Certified company/org code |
| `NON_CERT_COMPANY_ID()` | str | Non-certified company/org code |

---

## 4. Assertion Style

**Always use `assert`, never `return True/False`.** Pytest only marks a test as FAILED if an exception or `assert` failure is raised. Returning `False` silently passes.

```python
# ✅ Correct
assert response.status_code == 200, f"Expected 200, got {response.status_code}"
assert error_code == 0, f"Expected errorCode 0, got {error_code} — {data.get('message')}"

# ❌ Wrong — pytest ignores this
return False
```

Use `print()` with these emoji prefixes consistently:
- `✅` — step header or PASS
- `❌` — FAIL
- `📋` — data/value output
- `⚠️` — warning or unexpected but non-fatal result

---

## 5. Response Contract Assertions (mandatory in `_valid.py`)

After every successful API call in the valid test, assert the full response contract before checking business logic:

```python
# HTTP status
assert response.status_code == 200, f"Expected HTTP 200, got {response.status_code}"

# Content-Type
content_type = response.headers.get("Content-Type", "")
assert "application/json" in content_type, f"Expected application/json, got '{content_type}'"

# Valid JSON body
try:
    body = response.json()
except Exception as e:
    assert False, f"Response body is not valid JSON — {e}"

# Required fields
assert "errorCode" in body, "Required field 'errorCode' missing from response body"
assert isinstance(body["errorCode"], int), f"'errorCode' must be int, got {type(body['errorCode']).__name__}"
assert "message" in body, "Required field 'message' missing from response body"
assert isinstance(body["message"], str), f"'message' must be str, got {type(body['message']).__name__}"
```

---

## 6. Standard Test Categories Per File

### 6a. `_valid.py` — Happy Path

Steps to always include:

1. **Baseline** — if the endpoint modifies data, fetch current state first so it can be restored.
2. **Call the endpoint** with all valid parameters (required + optional).
3. **Contract assertions** — HTTP 200, Content-Type, errorCode (int), message (str) — see section 5.
4. **Business logic assertions** — assert that `errorCode == 0`, assert field values in the response `result`.
5. **Verify persistence** — call a GET endpoint to re-fetch and confirm changes were saved.
6. **Restore** — in `finally`, restore original data if anything was modified.

```python
# Typical structure
print("✅ [Step 1] Get baseline")
...
print("\n✅ [Step 2] Call endpoint with valid payload")
response = uid_client.some_method(...)
print("\n✅ [Step 2b] Assert response contract")
assert response.status_code == 200, ...
# ... contract assertions ...
print("\n✅ [Step 3] Verify changes persisted")
verify_response = uid_client.get_...()
assert verify_response.json().get("result", {}).get("someField") == expected_value, ...
```

### 6b. `_invalid.py` — Invalid Payload

Group tests into numbered Steps. Always include these groups:

**Step 1 — Missing required fields:**
```python
missing_tests = [
    {"name": "missing_fieldA", "field_a": None, "field_b": "valid"},
    {"name": "empty_fieldA",   "field_a": "",   "field_b": "valid"},
    {"name": "both_missing",   "field_a": None, "field_b": None},
]
```
Assert: `error_code != 0` OR `status_code in [400, 401, 403, 422]`.

**Step 2 — Invalid formats:**
Cover: wrong type, wrong enum value, out-of-range number, invalid email format, invalid phone format, invalid language/region code, wrong boolean type.

**Step 3 — Malicious payloads:**
Cover: XSS in string fields (`<script>alert(1)</script>`), SQL injection in string fields (`'; DROP TABLE users; --`), null byte injection (`test\x00admin`), oversized strings (1000+ characters).

**Step 4 — Non-existent IDs:**
For any `accountId`, `orgId`, `companyId`, or similar ID field: send a well-formed ID that does not exist in the system (e.g., `"00000000000001"`, `"99999999999999"`).
Assert: `error_code != 0` OR `status_code in [400, 404]`.

**Summary block** at the end:
```python
total = step1_passed + step2_passed + step3_passed + step4_passed
maximum = step1_total + step2_total + step3_total + step4_total
print(f"\n📊 Overall: {total}/{maximum} passed")
```

### 6c. `_header.py` — Header Validation

**Step 1 — Authorization failures:**
```python
auth_tests = [
    {"name": "no_auth_header",        "token": None,         "force_no_auth": True},
    {"name": "empty_token",           "token": "",           "force_no_auth": False},
    {"name": "invalid_token_format",  "token": "invalid_12345"},
    {"name": "malformed_bearer",      "token": "NotBearer abc"},
    {"name": "expired_like_token",    "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.expired.token"},
]
```
Assert: `status_code in [401, 403]`.

**Step 2 — Content-Type failures:**
```python
content_type_tests = [
    {"name": "missing_content_type", "Content-Type": ""},
    {"name": "text_plain",           "Content-Type": "text/plain"},
    {"name": "application_xml",      "Content-Type": "application/xml"},
]
```

**Step 3 — Malicious/injected headers:**
```python
malicious_header_tests = [
    {"name": "xss_injection",        "X-Injection": '<script>alert("xss")</script>'},
    {"name": "host_header_injection","Host": "malicious-host.com"},
    {"name": "x_forwarded_for",      "X-Forwarded-For": "127.0.0.1"},
    {"name": "crlf_injection",       "X-Test": "value\r\nX-Injected: malicious"},
    {"name": "oversized_header",     "X-Large": "x" * 8192},
]
```

Use `uid_client.some_method(..., custom_headers=test_headers)` to pass custom headers.
Use `uid_client.some_method(..., token=test_case["token"])` to override the auth token.

### 6d. `_invalid_method.py` — Wrong HTTP Methods

Test every non-native HTTP method. For a POST endpoint:

```python
method_tests = [
    {"method": "GET",     "expected_codes": [405, 400, 404]},
    {"method": "PUT",     "expected_codes": [405, 400]},
    {"method": "DELETE",  "expected_codes": [405, 400]},
    {"method": "PATCH",   "expected_codes": [405, 400]},
    {"method": "HEAD",    "expected_codes": [405, 400, 404]},
    {"method": "OPTIONS", "expected_codes": [200, 204, 405]},  # CORS pre-flight
]
```

Use `uid_client.some_method(..., method=test_case["method"])`.

End with a positive validation: confirm POST (the correct method) returns `errorCode == 0`.

---

## 7. Security Test File (optional, `_security.py`)

Create a fifth file `test_{TICKET}__post_{endpoint_name}_security.py` when the endpoint accepts an identity parameter (`accountId`, `userId`, `email`) that could be used for horizontal privilege escalation.

**Always include:**

1. **IDOR test** — Authenticate as User A (`UID_USER_NAME`), send User B's identity (`ORG_MEMBER_EMAIL` / `ORG_MEMBER_ACCOUNT_ID`) in the payload. Assert rejection.
2. **Post-attack verification** — Re-fetch User B's data and assert it was not modified.
3. **Identity mismatch tests** — User A's accountId + User B's email, and vice versa. Both should be rejected.

```python
attacker_client = Unified_ID_API(UID_USER_NAME())
victim_client   = Unified_ID_API(ORG_MEMBER_EMAIL())
try:
    ...
finally:
    attacker_client.close()
    victim_client.close()
```

Use proper `assert` for every security check — these must cause real test failures, not just print `❌`.

---

## 8. `Unified_ID_API` Method Signature Conventions

When an API method does not yet exist in `api/unified_id_api.py`, create it following this pattern:

```python
def method_name(
    self,
    required_param: str,
    optional_param: Optional[str] = None,
    token: Optional[str] = None,
    custom_headers: Optional[Dict[str, str]] = None,
    method: str = "POST",          # or "GET" — matches the endpoint's native HTTP method
) -> httpx.Response:
    """
    POST /api/v1/path/to/endpoint
    One-line description.
    """
    url = f"{self.service_url}/api/v1/path/to/endpoint"

    headers = {"Content-Type": "application/json"}

    if token is not None:
        if token:
            headers["Authorization"] = f"Bearer {token}"
    elif self.access_token:
        headers["Authorization"] = f"Bearer {self.access_token}"

    if custom_headers:
        headers_lower = {k.lower(): k for k in headers}
        for key, value in custom_headers.items():
            key_lower = key.lower()
            if key_lower in headers_lower:
                del headers[headers_lower[key_lower]]
            headers[key] = value

    payload = {}
    if required_param:
        payload["requiredParam"] = required_param
    if optional_param is not None:
        payload["optionalParam"] = optional_param

    method = method.upper()
    if method == "POST":
        response = self.client.post(url, headers=headers, json=payload)
    elif method == "GET":
        response = self.client.get(url, headers=headers, params=payload)
    elif method == "PUT":
        response = self.client.put(url, headers=headers, json=payload)
    elif method == "DELETE":
        response = self.client.delete(url, headers=headers)
    elif method == "PATCH":
        response = self.client.patch(url, headers=headers, json=payload)
    elif method == "HEAD":
        response = self.client.head(url, headers=headers)
    elif method == "OPTIONS":
        response = self.client.options(url, headers=headers)
    else:
        response = self.client.request(method, url, headers=headers, json=payload)

    return response
```

---

## 9. Test Isolation Checklist

Before finishing any `_valid.py` script, verify:

- [ ] Original data is fetched before modification.
- [ ] Restoration call is inside `finally` (not just inside `if error_code == 0`).
- [ ] The restore call is verified with its own status check.
- [ ] No test leaves permanently changed state in the test account.

---

## 10. Full Example — Minimal `_valid.py`

```python
from pytests.__init__ import *


def test_case():
    """
    [Step1] Authenticate and get current state for baseline
    [Step2] Call POST /api/v1/example with a valid payload
    [Step2b] Assert response contract (HTTP status, Content-Type, errorCode, message)
    [Step3] Verify the changes persisted
    [Step4] Restore original state
    """

    email = UID_USER_NAME()
    uid_client = Unified_ID_API(email)

    original_data = {}

    try:
        print("✅ [Step 1] Get baseline")
        info_response = uid_client.get_user_info()
        assert info_response.status_code == 200
        original_data = info_response.json().get("result", {})
        print(f"  📋 Current value: {original_data.get('someField')}")

        print("\n✅ [Step 2] Call endpoint with valid payload")
        response = uid_client.some_method(
            account_id=original_data.get("accountId"),
            email=email,
            some_field="new_value",
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
        assert "errorCode" in body, "Field 'errorCode' missing"
        assert isinstance(body["errorCode"], int), "'errorCode' must be int"
        assert "message" in body, "Field 'message' missing"
        assert isinstance(body["message"], str), "'message' must be str"
        print(f"  ✅ errorCode: {body['errorCode']} | message: '{body['message']}'")

        assert body["errorCode"] == 0, f"Expected errorCode 0, got {body['errorCode']} — {body.get('message')}"
        print("  ✅ PASS: Endpoint returned errorCode 0")

        print("\n✅ [Step 3] Verify changes persisted")
        verify = uid_client.get_user_info()
        assert verify.status_code == 200
        result = verify.json().get("result", {})
        assert result.get("someField") == "new_value", (
            f"Expected 'new_value', got '{result.get('someField')}'"
        )
        print(f"  ✅ PASS: someField is '{result.get('someField')}'")

    finally:
        if original_data:
            print("\n✅ [Step 4] Restore original state")
            uid_client.some_method(
                account_id=original_data.get("accountId"),
                email=email,
                some_field=original_data.get("someField"),
            )
        uid_client.close()
```
