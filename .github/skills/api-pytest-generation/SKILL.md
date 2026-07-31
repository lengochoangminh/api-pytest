---
name: api-pytest-generation
description: 'Generate a full pytest test suite for a SINGLE known Unified ID API endpoint. Use when: the user already knows exactly which endpoint to test and provides a method + path (e.g. POST /api/v1/login), a curl example, or a Swagger snippet. Produces _valid, _invalid, _header, _invalid_method, and (when applicable) _security test files, plus the API client method if missing. For discovering uncovered endpoints first, use the api-coverage-workflow skill instead.'
argument-hint: 'Endpoint to test, e.g. "POST /api/v1/login"'
---

# API Pytest Generation

Generates a complete pytest test suite for **one specified** Unified ID API endpoint, following every convention defined in `.github/instructions/api-test-generation.instructions.md`.

---

## When to Use

- The user already knows which endpoint to implement and provides the HTTP method + path
- Implementing a full test suite (valid + invalid + headers + method + security) for a specific operation
- **Not** for discovering coverage gaps — use `api-coverage-workflow` for that

---

## Inputs

The user must provide ONE of:

- An endpoint in the form `[METHOD] /api/v1/path` (e.g., `POST /api/v1/login`)
- A Swagger URL from which the operation can be fetched
- A curl example or natural-language description of the endpoint

If the endpoint is ambiguous, ask:

> "Which endpoint would you like to test? Provide the HTTP method and path, e.g. `POST /api/v1/login`."

---

## Procedure

### Step 1 — Resolve Endpoint Details

1. If the user gave only a Swagger URL, fetch `https://<host>/v3/api-docs` and locate the matching operation.
2. Extract:
   - HTTP method and path
   - Controller tag (used to derive the target folder)
   - Request body schema — which fields are required vs optional, their types
   - Whether the endpoint is **public** (no auth) or **authenticated**
3. Derive the **controller folder**: convert the controller tag to kebab-case (e.g., `tplink-id-controller`).

---

### Step 2 — Assign Ticket Numbers

1. List all files in `pytests/{controller-folder}/` matching `test_ES*.py`.
2. Find the highest existing ticket number (e.g., `ES2020903`).
3. Assign **base ticket = highest + 1**. The five files use: base, base+1, base+2, base+3, base+4.
4. Verify no ticket in the range base–base+4 already exists. If any are taken, skip to the next free block and note the deviation in the docstring.

---

### Step 3 — Check or Create the API Client Method

1. Search `api/unified_id_api.py` for a method that calls the endpoint path.
2. **If found**: use it as-is. Do **not** create a duplicate method.
3. **If not found**: create a new method using the template in section 8 of the instruction file.

Key rules for the new method:

- **Public endpoint** (no auth required): use `API_BASE_URL()` for the URL, omit the default `Authorization` header — only inject it when `token` is explicitly passed.
- **Authenticated endpoint**: use `self.service_url`, include the standard `Authorization: Bearer` header logic.
- Always implement the full `custom_headers` merge loop (case-insensitive key deduplication).
- Always implement the full method-dispatch block (`POST`, `GET`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS`, fallback `request`).
- Do **not** call `raise_for_status()` — return the raw response so tests can assert on any status code.

---

### Step 4 — Generate Test Files

Generate all four (or five) test files. **Read and follow every rule** in `.github/instructions/api-test-generation.instructions.md`.

| File | Suffix | Always? |
|------|--------|---------|
| Happy path | `_valid.py` | ✅ Yes |
| Invalid payload | `_invalid.py` | ✅ Yes |
| Header validation | `_header.py` | ✅ Yes |
| Wrong HTTP method | `_invalid_method.py` | ✅ Yes |
| Security / AuthZ | `_security.py` | Only when payload contains `accountId`, `userId`, or `email` |

**Critical reminders:**

- `from pytests.__init__ import *` is the **only** import line — nothing else.
- Single function `test_case()` with no parameters.
- All steps wrapped in `try/finally uid_client.close()`.
- `_invalid.py` **must** end with the `📊 Overall: {total}/{maximum} passed` summary block.
- `_valid.py` **must** restore original state in `finally` if the endpoint modifies any data.
- `_header.py` for **public endpoints**: skip the auth-token failure cases (Step 1 of the standard header group) because unauthenticated calls are expected to succeed — adapt the step list accordingly and document the reason.

---

### Step 5 — Validate

After creating all files, run `get_errors()` on:

- Every new test file
- `api/unified_id_api.py` (for any new method)

Fix any reported errors before reporting completion.

---

### Step 6 — Report

Summarise results clearly:

- API method: **created** (name, signature) or **existing** (name, any changes made)
- Files created: one line per file with path and ticket number
- Any deviations from the standard 5-file / base+4 ticket numbering pattern
