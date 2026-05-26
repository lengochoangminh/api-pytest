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
- **Comprehensive coverage** — every endpoint is covered across four dimensions: valid inputs, invalid inputs, header validation, and wrong HTTP method

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
pytest --env staging

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
├── api/
│   └── unified_id_api.py          # HTTP client for all Unified ID endpoints
├── logs/
│   └── log<YYYY-MM-DD>.txt        # Daily rotating log file
├── pytests/
│   ├── __init__.py                # Shared imports used by every test module
│   ├── test_ES1455067__post_updateInfo_valid.py
│   ├── test_ES1455068__post_updateInfo_invalid.py
│   ├── test_ES1455069__post_updateInfo_header.py
│   ├── test_ES1455070__post_updateInfo_invalid_method.py
│   ├── test_ES2020886__post_changeOwner_valid.py
│   ├── test_ES2020887__post_changeOwner_invalid.py
│   ├── test_ES2020888__post_changeOwner_header.py
│   ├── test_ES2020889__post_changeOwner_invalid_method.py
│   ├── test_ES2020890__get_getLinkToSubsystem_valid.py
│   ├── test_ES2020891__get_getLinkToSubsystem_invalid.py
│   ├── test_ES2020892__get_getLinkToSubsystem_header.py
│   └── test_ES2020893__get_getLinkToSubsystem_invalid_method.py
├── utilities/
│   ├── helpers.py                 # Utility class: random data, UUID, session code, TOTP
│   └── log_util.py                # Logger wrapper with Allure step integration
├── config.py                      # Env var accessors (loaded by conftest)
├── conftest.py                    # pytest hooks, CLI options, session fixtures
├── pytest.ini                     # pytest configuration (paths, reruns, filters)
└── requirements.txt               # Python dependencies
```

### Test file naming convention

```
test_<TICKET_ID>__<method>_<endpoint>_<scenario>.py
       │              │         │           │
       │              │         │           └─ valid | invalid | header | invalid_method
       │              │         └─────────── endpoint name (camelCase)
       │              └───────────────────── HTTP method (get | post | put | delete)
       └──────────────────────────────────── Jira / tracker ticket ID
```
