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
| Performance testing | [Locust](https://locust.io/) |

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
  performance-test/  ← Locust performance / load test scripts
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
│   └── instructions/
│       └── api-test-generation.instructions.md   # Conventions applied automatically when creating tests under pytests/
│   └── skills/
│       └── api-coverage-workflow   # Fetch the Swagger, compute coverage gaps, let the user pick endpoints, then generate full pytest suites for each selection.
│       └── api-pytest-generation   # Generates pytest test suite for one specified Unified ID API endpoint
├── api/
│   └── unified_id_api.py          # HTTP client for all Unified ID endpoints
├── logs/
│   └── log<YYYY-MM-DD>.txt        # Daily rotating log file
├── pytests/
│   ├── __init__.py                # Shared imports used by every test module
│   ├── api-test/
│   │   ├── organization-controller/   # Tests for organization management endpoints
│   │   ├── tplink-id-controller/      # Tests for TP-Link ID / subsystem endpoints
│   │   └── user-center-controller/    # Tests for user profile endpoints
│   └── performance-test/
│       └── locustfile_updateInfo.py   # Locust load test — POST /api/v1/account/updateInfo
├── utilities/
│   ├── helpers.py                 # Utility class: random data, UUID, session code, TOTP
│   └── log_util.py                # Logger wrapper with Allure step integration
├── config.py                      # Env var accessors (loaded by conftest)
├── conftest.py                    # pytest hooks, CLI options, session fixtures
├── pytest.ini                     # pytest configuration (paths, reruns, filters)
└── requirements.txt               # Python dependencies
```

---

# Performance Tests

Load and performance tests for the Unified ID API, built with [Locust 2.x](https://locust.io/).

```
performance-test/
├── common/
│   ├── auth.py            ← credential pool + make_api_client() factory
│   └── shapes.py          ← reusable LoadTestShape classes (StagesShape, SoakShape, SpikeShape)
├── scenarios/
│   └── user_journey.py    ← realistic multi-endpoint user flow (write + read)
├── perf_updateInfo.py     ← focused load test: POST /api/v1/account/updateInfo
├── perf_userInfo.py       ← utility users: GET /api/v1/user-info (latency + soak/stress)
└── README.md              ← this file
```

---

## Adding Tests for a New Endpoint

Two **GitHub Copilot skills** automate test generation. Type `/` in the chat panel to invoke either one.

### `api-coverage-workflow` — discover gaps then implement (recommended starting point)

```
/api-coverage-workflow https://aps1-api-id-alpha2.tplinkcloud.com/swagger-ui/index.html#/
```

| Step | What happens |
|------|-------------|
| 1 | Fetches the live Swagger spec (`/v3/api-docs`) |
| 2 | Scans `pytests/` to detect which endpoints already have tests |
| 3 | Prints a numbered list of uncovered endpoints grouped by controller |
| 4 | **Waits** for you to select: a number, comma-separated numbers, or `ALL` |
| 5 | For each selected endpoint, runs the full test generation workflow (tickets → API method → 4–5 test files → validation) |
| 6 | Prints a session summary table when done |

Skill definition: `.github/skills/api-coverage-workflow/SKILL.md`

---

### `api-pytest-generation` — implement one known endpoint directly

```
/api-pytest-generation POST /api/v1/login
```

Use this when you already know exactly which endpoint to test. Skips the gap-analysis phase and goes straight to generation.

| Step | What happens |
|------|-------------|
| 1 | Resolves endpoint details (method, path, schema, auth requirement) |
| 2 | Scans the target controller folder and assigns the next available ticket block |
| 3 | Creates (or verifies) the `Unified_ID_API` client method in `api/unified_id_api.py` |
| 4 | Generates all 4–5 test files (`_valid`, `_invalid`, `_header`, `_invalid_method`, optionally `_security`) |
| 5 | Runs `get_errors()` on every new file and reports a summary |

Skill definition: `.github/skills/api-pytest-generation/SKILL.md`

---

### Manual / background context

When working inside `pytests/`, GitHub Copilot automatically loads `.github/instructions/api-test-generation.instructions.md`. It encodes all naming conventions, assertion style, per-file test categories, security patterns, and the `Unified_ID_API` method template. You can also paste a Swagger spec or curl example directly in chat without invoking a skill.
