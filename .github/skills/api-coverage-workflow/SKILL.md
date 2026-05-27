---
name: api-coverage-workflow
description: 'Interactive coverage gap analysis + test generation for the Unified ID API. Use when: user provides a Swagger URL and wants to discover which endpoints are NOT yet tested; user wants to select one, several, or ALL uncovered endpoints to implement. Workflow: fetch spec → scan pytests/ to detect covered endpoints → display numbered uncovered list grouped by controller → user selects → generate tests using api-pytest-generation conventions.'
argument-hint: 'Swagger UI or spec URL, e.g. https://host/swagger-ui/index.html'
---

# API Coverage Gap Analysis + Test Generation

Interactive workflow: fetch the live Swagger spec, compute coverage gaps, let the user pick endpoints, then generate full pytest suites for each selection.

---

## When to Use

- User provides a Swagger URL and wants to know which endpoints are not yet tested
- User wants to select one endpoint, a subset, or all uncovered endpoints to implement in one session
- For implementing a **single already-known** endpoint directly, use `api-pytest-generation` instead

---

## Inputs

Required: A Swagger URL (UI or spec JSON). Examples:

- `https://aps1-api-id-alpha2.tplinkcloud.com/swagger-ui/index.html#/`
- `https://aps1-api-id-alpha2.tplinkcloud.com/v3/api-docs`

---

## Procedure

### Phase 1 — Fetch the OpenAPI Spec

1. Derive the spec JSON URL:
   - If the URL contains `/swagger-ui/`, replace that segment and everything after it with `/v3/api-docs`.
   - If the URL already ends in `/v3/api-docs` or `/api-docs`, use it as-is.
2. Fetch the spec and extract every operation: for each `path × HTTP verb`, collect `{ method, path, tag, summary }`.
3. Keep only standard verbs: `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, `OPTIONS`, `HEAD`.

---

### Phase 2 — Detect Covered Endpoints

4. For each swagger operation, determine if a `_valid.py` test already exists:
   - Search the endpoint path string (e.g., `/api/v1/register`) across all `*.py` files under `pytests/` using `grep_search` with `includePattern: "pytests/**"`.
   - An operation is **covered** if its path appears in at least one file in `pytests/`.
5. Build two sets: **covered** and **uncovered** operations.
6. Compute totals: covered count, uncovered count, total.

---

### Phase 3 — Display the Gap List

7. Print the summary line:
   ```
   📊 Coverage: {covered}/{total} operations covered — {uncovered} missing tests
   ```
8. Print the uncovered operations as a **single sequential numbered list**, grouped by controller tag (sorted A–Z), then sorted by path within each group:
   ```
   ### controller-tag-name
    1. [POST] /api/v1/path/one  —  Summary text
    2. [GET]  /api/v1/path/two  —  Summary text

   ### another-controller
    3. [DELETE] /api/v1/other  —  Summary text
   ```
   Numbers run consecutively across all groups so the user can reference any item by a single number.

---

### Phase 4 — User Selection

9. After displaying the list, ask:
   > "Which endpoint(s) would you like to implement? Enter a number, comma-separated numbers (e.g. `1, 5, 12`), or `ALL`."
10. **Wait** for the user's reply before doing any implementation.

---

### Phase 5 — Generate Tests

11. Parse the user's reply:
    - A single number → one endpoint.
    - Comma-separated numbers → the listed subset.
    - `ALL` → every uncovered endpoint from the list.
12. For **each** selected endpoint (in list order):
    a. Run the full implementation workflow from `api-pytest-generation` (steps 1–6 of `.github/skills/api-pytest-generation/SKILL.md`):
       - Resolve endpoint details from the already-fetched spec (no re-fetch needed).
       - Assign ticket numbers (scan the target folder).
       - Check or create the `Unified_ID_API` client method.
       - Generate `_valid`, `_invalid`, `_header`, `_invalid_method`, and (if applicable) `_security` test files.
       - Validate with `get_errors()`.
    b. After each endpoint is done, print a brief confirmation:
       ```
       ✅ Done: [POST] /api/v1/path — tickets ES######–ES######, 5 files created
       ```
    c. If `ALL` is selected and there are many endpoints, process them sequentially and keep a running progress line:
       ```
       ⏳ Progress: 3/12 endpoints complete
       ```
13. When all selected endpoints are done, print a final summary table:
    ```
    📋 Session summary
    | Endpoint                    | Tickets         | Files |
    |-----------------------------|-----------------|-------|
    | POST /api/v1/login          | ES######–###### | 5     |
    | GET  /api/v1/user-info      | ES######–###### | 4     |
    ```
