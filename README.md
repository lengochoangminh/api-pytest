# API Test Automation — Unified ID API

Automated API test suite for the **Unified ID** service, covering user profile management, organization ownership, and subsystem integration endpoints.

---

## Features

- **Multi-environment support** — switch between environments (e.g., `beta_use1`, `staging`) via a CLI flag with no code changes
- **Token caching** — authentication tokens are persisted to `.secret/auth_tokens.json` and reused across tests to reduce login overhead
- **Auto retry** — flaky tests are automatically re-run (1 retry, 1-second delay) before being marked as failures
- **Parallel execution** — tests can run concurrently using `pytest-xdist` to shorten overall suite duration
- **Allure reporting** — each test step is wrapped in an Allure step for rich, structured HTML reports
- **Structured logging** — daily rotating log files written to `logs/` with timestamp, file name, and line number context
- **Test isolation** — valid-payload tests restore original data after assertions so account state is never permanently altered
- **Comprehensive coverage** — every endpoint is covered across five dimensions: valid inputs, invalid inputs, header validation, wrong HTTP method, and security/authorization

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Test framework | [pytest](https://docs.pytest.org/) |
| HTTP client | [httpx](https://www.python-httpx.org/) |
| Reporting | [Allure](https://allurereport.org/) (`allure-pytest`) |
| Parallel runs | [pytest-xdist](https://pytest-xdist.readthedocs.io/) |
| Test data generation | [Faker](https://faker.readthedocs.io/) |
| OTP generation | [pyotp](https://pyauth.github.io/pyotp/) |
| Environment config | [python-dotenv](https://pypi.org/project/python-dotenv/) |
| Retry on failure | [pytest-rerunfailures](https://github.com/pytest-dev/pytest-rerunfailures) |

---

## Architecture

```
conftest.py          ← session-scoped fixture loads .env based on --env flag
     │
     ▼
config.py            ← exposes typed accessors (API_BASE_URL, UID_PWD, …) from env vars
     │
     ▼
api/
  unified_id_api.py  ← API client: authenticates, caches tokens, wraps every endpoint
     │
     ▼
pytests/
  __init__.py        ← shared imports (API client, config, helpers, logger)
  test_*.py          ← individual test modules; one function per file
```

**Request flow for each test:**

```
test_*.py
  └─► Unified_ID_API(email)        # authenticates or loads cached token
        └─► httpx.Client           # sends HTTP request with auth headers
              └─► API server       # returns JSON response
  └─► assertions on status code, errorCode, and result body
```

**Environment files** are stored in `.env/` and are not committed to source control:

```
.env/
  .env.beta_use1      ← default
  .env.staging
  .env.<custom>
```

---

## Installation

### Prerequisites

- Python 3.10 or newer
- [Allure CLI](https://allurereport.org/docs/install/) (optional, for HTML reports)

### Steps

```bash
# 1. Clone the repository
git clone <repo-url>
cd api-pytest

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create environment file(s)
mkdir .env
copy .env\.env.beta_use1.example .env\.env.beta_use1   # if an example is provided
# then fill in the actual values
```

**Minimum required variables in your `.env` file:**

```dotenv
API_BASE_URL=https://<host>

# User account
UID_PWD=<password>
UID_ACCOUNT_ID=<account-id>
UID_USER_NAME=<email>

# Organisation
CERT_COMPANY_ID=<id>
CERT_COMPANY_NAME=<name>
ORG_OWNER_EMAIL=<email>
ORG_OWNER_ACCOUNT_ID=<id>
NON_CERT_COMPANY_ID=<id>
NON_CERT_COMPANY_NAME=<name>
ORG_MEMBER_EMAIL=<email>
ORG_MEMBER_ACCOUNT_ID=<id>
```

### Running Tests

```bash
# Run all tests against the default environment (beta_use1)
pytest

# Run against a specific environment
pytest --env=beta_use1

# Run a specific test file
pytest pytests/test_ES1455067__post_updateInfo_valid.py

# Run in parallel (4 workers)
pytest -n 4

# Generate an Allure report
pytest --alluredir=allure-results
allure serve allure-results
```

---

## Project Structure

```
api-pytest/
├── .env/                          # Environment variable files (git-ignored)
│   └── .env.beta_use1             # Default environment config
├── .secret/                       # Runtime secrets / token cache (git-ignored)
│   └── auth_tokens.json           # Cached auth tokens (auto-generated)
├── .github/
│   ├── agents/
│   │   └── qa-subagent.agent.md   # Custom QA agent definition for Copilot
│   └── instructions/
│       └── api-test-generation.instructions.md   # Conventions applied automatically when creating tests under pytests/
├── api/
│   └── unified_id_api.py          # HTTP client for all Unified ID endpoints
├── logs/
│   └── log<YYYY-MM-DD>.txt        # Daily rotating log file
├── pytests/
│   ├── __init__.py                # Shared imports used by every test module
│   ├── organization-controller/   # Tests for organization management endpoints
│   ├── tplink-id-controller/      # Tests for TP-Link ID / subsystem endpoints
│   └── user-center-controller/    # Tests for user profile endpoints
├── utilities/
│   ├── helpers.py                 # Utility class: random data, UUID, session code, TOTP
│   └── log_util.py                # Logger wrapper with Allure step integration
├── config.py                      # Env var accessors (loaded by conftest)
├── conftest.py                    # pytest hooks, CLI options, session fixtures
├── pytest.ini                     # pytest configuration (paths, reruns, filters)
└── requirements.txt               # Python dependencies
```

---

## Test Coverage

Each endpoint is covered by up to **five test files**, one per concern. The table below lists every file and the exact scenarios it exercises.

### Convention — file suffix → concern

| Suffix | Concern |
|--------|---------|
| `_valid` | Happy path: valid inputs, response contract, field persistence, data restore |
| `_invalid` | Negative: missing fields, bad formats, malicious payloads, non-existent IDs |
| `_header` | Auth failures, wrong Content-Type, malicious/injected headers |
| `_invalid_method` | Wrong HTTP methods (GET/PUT/DELETE/PATCH/HEAD/OPTIONS against the endpoint) |
| `_security` | IDOR, cross-account access, token vs payload identity mismatch |

---

### `user-center-controller` — `POST /api/v1/account/updateInfo`

Updates the authenticated user's profile (`firstName`, `lastName`, `phone`, `language`, `region`, `use24hour`).

#### ES1455067 — `_valid`
| # | Scenario |
|---|----------|
| 1 | Fetch current profile as baseline before any change |
| 2 | Update all fields (`firstName`, `lastName`, `phone`, `language`, `region`, `use24hour: true`) with valid values |
| 2b | Assert response contract: HTTP 200, `Content-Type: application/json`, `errorCode` is `int`, `message` is `str` |
| 3 | Re-fetch profile and verify every updated field persisted |
| 4 | Restore original profile data in `finally` for test isolation |

#### ES1455068 — `_invalid`
| # | Scenario |
|---|----------|
| 1a | Missing `accountId` (null) |
| 1b | Missing `email` (null) |
| 1c | Empty string `accountId` |
| 1d | Empty string `email` |
| 1e | Both `accountId` and `email` missing |
| 2a | Invalid email format (`not-an-email`) |
| 2b | Invalid phone format (`abc123`) |
| 2c | Invalid language code (`invalid_lang_code`) |
| 2d | Invalid region code (`XX`) |
| 2e | Wrong type for `use24hour` (string instead of boolean) |
| 3a | XSS payload in `firstName` (`<script>alert(1)</script>`) |
| 3b | XSS payload in `lastName` (`<img onerror=...>`) |
| 3c | SQL injection in `phone` (`'; DROP TABLE users; --`) |
| 3d | Oversized string in `firstName` (1 000 characters) |
| 3e | Null-byte injection in `lastName` (`test\x00admin`) |
| 4a | Well-formed but non-existent `accountId` (`00000000000001`) |
| 4b | Upper-boundary non-existent `accountId` (`99999999999999`) |

#### ES1455069 — `_header`
| # | Scenario |
|---|----------|
| 1a | No `Authorization` header at all |
| 1b | Empty Bearer token |
| 1c | Malformed token string (not a JWT) |
| 1d | `NotBearer` prefix instead of `Bearer` |
| 1e | Expired-format JWT |
| 2a | `Content-Type: ""` (blank) |
| 2b | `Content-Type: text/plain` |
| 2c | `Content-Type: application/xml` |
| 2d | `Content-Type: application/json; charset=invalid` |
| 3a | XSS value in custom header |
| 3b | Host header injection |
| 3c | `X-Forwarded-For: 127.0.0.1` spoofing |
| 3d | CRLF injection in custom header value |
| 3e | Oversized header value (8 KB) |

#### ES1455070 — `_invalid_method`
| # | Scenario |
|---|----------|
| 1 | `GET` — expect 405/400/404 |
| 2 | `PUT` — expect 405/400 |
| 3 | `DELETE` — expect 405/400 |
| 4 | `PATCH` — expect 405/400 |
| 5 | `HEAD` — expect 405/400/404 |
| 6 | `OPTIONS` — expect 200/204 (CORS pre-flight) or 405 |
| 7 | `POST` (positive) — confirm the correct method returns `errorCode 0` |

#### ES1455071 — `_security`
| # | Scenario |
|---|----------|
| 1 | **IDOR**: Authenticate as User A, send User B's `accountId` + `email` — expect rejection |
| 2 | **Silent write check**: Re-fetch User B's profile after the IDOR attempt and assert it is unchanged |
| 3a | **Identity mismatch**: User A's `accountId` + User B's `email` — expect rejection |
| 3b | **Identity mismatch**: User B's `accountId` + User A's `email` — expect rejection |

---

### `organization-controller` — `POST /api/v1/organization/changeOwner`

Transfers organization ownership from the current owner to another member.

#### ES2020886 — `_valid`
| # | Scenario |
|---|----------|
| 1 | Authenticate as org owner; log owner email, org code, and intended new owner |
| 2 | Call `changeOwner` API to transfer ownership to an existing org admin |
| 2b | Assert response contract: HTTP 200, `Content-Type: application/json`, `errorCode` is `int`, `message` is `str` |
| 3 | Assert `errorCode == 0` — ownership transferred successfully |
| 4 | Restore original ownership (transfer back) in `finally` |

#### ES2020887 — `_invalid`
| # | Scenario |
|---|----------|
| 1a | Missing `email` (null) |
| 1b | Empty string `email` |
| 1c | Whitespace-only `email` |
| 2a | Invalid email format (no `@`) |
| 2b | Missing domain part (`user@`) |
| 2c | Missing local part (`@example.com`) |
| 2d | Double `@` sign |
| 2e | Unregistered email (well-formed but not in system) |
| 2f | Non-admin org member email (valid account, insufficient role) |
| 2g | Owner self-transfer (email == authenticated owner) |
| 3a | Non-existent org code |
| 3b | Empty org code |
| 3c | Special characters in org code (`!@#$%`) |
| 3d | SQL injection in org code |
| 4a | XSS payload in `email` field |
| 4b | SQL injection in `email` field |
| 4c | Oversized string in `email` (1 000+ chars) |
| 4d | Null-byte injection in `email` |
| 4e | HTML injection in `email` |

#### ES2020888 — `_header`
| # | Scenario |
|---|----------|
| 1a–1e | Auth header failures (none, empty, invalid, malformed Bearer, expired JWT) |
| 2a–2c | Wrong `Content-Type` values (blank, `text/plain`, `application/xml`) |
| 3a–3e | Malicious/injected headers (XSS, Host injection, X-Forwarded-For, CRLF, oversized) |
| 4a | Non-owner org member attempts `changeOwner` — expect rejection |
| 4b | Org admin (non-owner) attempts `changeOwner` — expect rejection |

#### ES2020889 — `_invalid_method`
| # | Scenario |
|---|----------|
| 1–6 | `GET`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS` — all expect rejection |
| 7 | `POST` (positive) — confirm correct method succeeds |

#### ES2020894 — `_security`
| # | Scenario |
|---|----------|
| 1 | **Non-owner AuthZ bypass**: org member (not owner) calls `changeOwner` on `CERT_COMPANY_ID` using their own valid token — expect rejection |
| 2 | **Cross-org attack**: cert org owner calls `changeOwner` on `NON_CERT_COMPANY_ID` — expect rejection |
| 3 | **Post-attack verification**: owner self-transfer probe confirms they still own `CERT_COMPANY_ID` (domain error expected, not `errorCode 0`) |

---

### `tplink-id-controller` — `GET /api/v1/get-link-to-subsystem`

Returns a redirect URL to a TP-Link subsystem (e.g., Omada Cloud Portal) for the authenticated user.

#### ES2020890 — `_valid`
| # | Scenario |
|---|----------|
| 1 | Call `GET /api/v1/get-link-to-subsystem` with `clientId=omada-cloud-portal` |
| 2 | Assert response contract: HTTP 200, `Content-Type: application/json`, `errorCode` is `int`, `message` is `str` |
| 3 | Assert `errorCode == 0`; verify `result.name` and `result.homeUrl` are non-empty |

#### ES2020891 — `_invalid`
| # | Scenario |
|---|----------|
| 1 | Missing `clientId` parameter |
| 2a | Empty string `clientId` |
| 2b | Whitespace-only `clientId` |
| 3a | Unknown/unsupported `clientId` string |
| 3b | Non-existent subsystem name |
| 3c | Numeric-only `clientId` |
| 4a | XSS payload in `clientId` |
| 4b | SQL injection in `clientId` |
| 4c | Oversized string in `clientId` |

#### ES2020892 — `_header`
| # | Scenario |
|---|----------|
| 1a–1e | Auth header failures (none, empty, invalid, malformed Bearer, expired JWT) |
| 2a–2c | Wrong `Content-Type` values |
| 3a–3e | Malicious/injected headers (XSS, Host injection, X-Forwarded-For, CRLF, oversized) |

#### ES2020893 — `_invalid_method`
| # | Scenario |
|---|----------|
| 1–6 | `POST`, `PUT`, `DELETE`, `PATCH`, `HEAD`, `OPTIONS` — all expect rejection |
| 7 | `GET` (positive) — confirm correct method succeeds |

---

## Adding Tests for a New Endpoint

The file `.github/instructions/api-test-generation.instructions.md` is automatically applied by GitHub Copilot when working inside `pytests/`. It encodes all naming conventions, assertion style, per-file test categories, security patterns, and the `Unified_ID_API` method template. Paste a Swagger spec or curl example in the chat and Copilot will generate the full set of test files.
