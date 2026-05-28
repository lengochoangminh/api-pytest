# Performance Tests — Unified ID API

Load and performance tests for the Unified ID API, built with [Locust 2.x](https://locust.io/).

---

## Folder Structure

```
performance-test/
├── common/
│   ├── auth.py            ← credential pool + make_api_client() factory
│   └── shapes.py          ← reusable LoadTestShape classes (StagesShape, SoakShape, SpikeShape)
├── scenarios/
│   └── user_journey.py    ← realistic multi-endpoint user flow (write + read)
├── perf_authFlow.py       ← auth cycle test: full 3-step OAuth flow (login → authorize → token)
├── perf_updateInfo.py     ← focused load test: POST /api/v1/account/updateInfo
├── perf_userInfo.py       ← utility users: GET /api/v1/user-info (latency + soak/stress)
└── README.md              ← this file
```

---

## Design Principles

### 1. User class vs. Shape — separation of concerns

| Responsibility | Where it lives |
|---|---|
| What to call (endpoint, payload, assertions) | User class (`task` methods) |
| How many users, ramp speed, duration | `LoadTestShape` in `common/shapes.py` |

This means a single user class can be driven as a stress test, a soak test, or a spike test just by swapping the imported shape — no code changes needed in the user class.

### 2. Auth strategy

Every virtual user authenticates **once** in `on_start()` via the existing `Unified_ID_API` wrapper, which handles the full 3-step OAuth flow (login → OAuth redirect → token exchange). The resulting `access_token` and `service_url` are reused for the entire lifetime of that virtual user.

Auth failures are emitted as Locust error events so they appear in the web UI and HTML report.

### 3. Test isolation

Valid-payload users snapshot the original profile in `on_start()` and restore it in `on_stop()`, so test accounts are never left in a modified state after the run.

### 4. Failure definition

HTTP 200 alone is not enough. Every task also checks `errorCode == 0` in the response body. A `200 OK` with `errorCode != 0` is counted as a **Locust failure**, so the web UI failure rate reflects real business errors, not just HTTP errors.

---

## Shared Modules (`common/`)

### `common/auth.py`

- Builds a credential pool from env-var accounts (`UID_USER_NAME`, `ORG_OWNER_EMAIL`, `ORG_ADMIN_EMAIL`, `ORG_ADMIN_EMAIL_2`, `ORG_MEMBER_EMAIL`).
- Cycles through accounts in a thread-safe (gevent-safe) round-robin so virtual users don't all share one session.
- Calls `load_env()` at import time — scenario files do **not** need to call it.
- Exposes `make_api_client(fire_event_fn=...)` which authenticates and returns a ready `Unified_ID_API` instance.

### `common/shapes.py`

Three reusable `LoadTestShape` classes. Import the one you need into your scenario file — Locust discovers it automatically via the module namespace.

| Shape | Duration | Peak users | Purpose |
|---|---|---|---|
| `StagesShape` | 8 min (self-terminating) | 50 | Staged warm-up → ramp → peak → ramp-down |
| `SoakShape` | Controlled by `--run-time` | 20 | Flat sustained load (memory leak, drift detection) |
| `SpikeShape` | 4 min (self-terminating) | 200 | Sudden traffic spike, then recovery |

> **Note:** when any `LoadTestShape` is active, Locust disables the "Number of Users" and "Ramp Up" fields in the web UI — the shape has full control. Remove or comment out the shape import to re-enable manual control.

---

## Test Scripts

### `perf_authFlow.py` — Full OAuth authentication cycle

**Targets:** `POST /api/v1/login` → `GET {serviceUrl}/oauth/authorize` → `POST {serviceUrl}/api/v1/token`  
**Shape:** `StagesShape` (8 minutes, self-terminating)

Each of the three OAuth steps is timed individually so bottlenecks within the flow are visible. A composite "full cycle" event is also fired for end-to-end latency tracking.

| Focus | Detail |
|---|---|
| Memory leak detection | A fresh `httpx.Client` is created **and explicitly closed** after every task iteration — directly probing whether TCP connections accumulate across repeated auth cycles |
| Per-step visibility | Login, OAuth redirect, and token-exchange latencies are reported as separate Locust events |
| Composite metric | A single "full cycle" event captures the three-hop round-trip end-to-end |

Success criteria (auth flow is inherently slower due to 3-hop round trip):

| Metric | Target |
|---|---|
| HTTP status | `200` on login + token exchange; `302`/`307` on OAuth authorize |
| Business logic | `errorCode == 0` in login and token JSON responses |
| p95 response time | < 5 000 ms |
| p99 response time | < 10 000 ms |
| Failure rate | < 1 % |

```bash
# Web UI (manual start at http://localhost:8089)
locust -f pytests/performance-test/perf_authFlow.py

# Headless — StagesShape drives everything
locust -f pytests/performance-test/perf_authFlow.py --headless

# Soak — swap StagesShape → SoakShape in the import, then:
locust -f pytests/performance-test/perf_authFlow.py --headless --run-time 3h

# Spike — swap StagesShape → SpikeShape in the import, then:
locust -f pytests/performance-test/perf_authFlow.py --headless
```

---

### `perf_updateInfo.py` — Focused endpoint test

**Target:** `POST /api/v1/account/updateInfo`  
**Shape:** `StagesShape` (8 minutes, self-terminating)

| Task | Weight | Description |
|---|---|---|
| `update_full_profile` | 3 | All optional fields; name / language / phone randomised each call |
| `update_minimal` | 1 | Required fields only (`accountId` + `email`) |

Use this when you need to isolate and measure the SLA of the `updateInfo` endpoint specifically, independent of any other endpoint behaviour.

```bash
# Web UI (manual start at http://localhost:8089)
locust -f pytests/performance-test/perf_updateInfo.py

# Headless — StagesShape drives everything
locust -f pytests/performance-test/perf_updateInfo.py --headless
```

---

### `scenarios/user_journey.py` — Realistic user flow

**Targets:** `POST /api/v1/account/updateInfo` (weight 3) + `GET /api/v1/user-info` (weight 1)  
**Shape:** `StagesShape` by default (swap import to `SoakShape` or `SpikeShape`)

Simulates a realistic user session: update profile → verify the change. The 3:1 write:read ratio reveals contention and caching behaviour that single-endpoint tests miss.

```bash
# Default — 8-min staged ramp
locust -f pytests/performance-test/scenarios/user_journey.py --headless

# 2-hour soak — swap the shape import to SoakShape first, then:
locust -f pytests/performance-test/scenarios/user_journey.py --headless --run-time 2h

# Spike test — swap the shape import to SpikeShape first, then:
locust -f pytests/performance-test/scenarios/user_journey.py --headless
```

---

### `perf_userInfo.py` — Utility users for `GET /api/v1/user-info`

**Target:** `GET /api/v1/user-info`  
**Shape:** none built-in — drive manually with `-u`/`-r`/`--run-time` flags

Contains four user classes selectable with `--class-picker`:

| Class | Base | Purpose |
|---|---|---|
| `LatencySimulationUser` | `User` | Adds artificial client-side delay (slow_3g / fast_3g / 4g / wifi profiles) before each request. Validates timeout handling and connection resilience. |
| `UserInfoUser` | `User` | Clean minimal GET with periodic per-user stats logging. Use with `-u`/`-r` for stress, or `--run-time 2h` for soak. |
| `ParameterVariationUser` | `HttpUser` | Sends valid, invalid-token, missing-auth, and empty-token requests (5:2:1:1 ratio) to verify authentication error handling under load. |
| `ConcurrentRequestUser` | `HttpUser` | Fires bursts of 10 parallel requests via gevent `Pool` every 5 s. Reveals connection-pool exhaustion and response-time variance under burst traffic. |

```bash
# Pick a user class interactively in the web UI
locust -f pytests/performance-test/perf_userInfo.py --class-picker

# Headless stress run — UserInfoUser (20 users, 5 minutes)
locust -f pytests/performance-test/perf_userInfo.py --headless -u 20 -r 5 --run-time 5m --class UserInfoUser

# Headless 2-hour soak — UserInfoUser
locust -f pytests/performance-test/perf_userInfo.py --headless -u 20 -r 2 --run-time 2h --class UserInfoUser

# Concurrent burst test (5 users × 10 req/burst)
locust -f pytests/performance-test/perf_userInfo.py --headless -u 5 -r 1 --run-time 5m --class ConcurrentRequestUser

# Auth-variation test (invalid / missing / empty tokens under load)
locust -f pytests/performance-test/perf_userInfo.py --headless -u 10 -r 2 --run-time 5m --class ParameterVariationUser
```

---

## Success Criteria

Default targets for `perf_updateInfo.py`, `perf_userInfo.py`, and `scenarios/user_journey.py`:

| Metric | Target |
|---|---|
| HTTP status | `200` on every request |
| Business logic | `errorCode == 0` in response body |
| p95 response time | < 2 000 ms |
| p99 response time | < 5 000 ms |
| Failure rate | < 1 % |

> **`perf_authFlow.py` uses higher latency thresholds** (p95 < 5 000 ms, p99 < 10 000 ms) because the full 3-step OAuth flow is a 3-hop round trip by design.

---

## Environment Configuration

Scripts inherit the project's standard `.env` system. The `env` variable selects the environment file:

```bash
# Uses .env/.env.beta_use1 (default)
locust -f pytests/performance-test/perf_updateInfo.py --headless

# Uses .env/.env.staging
env=staging locust -f pytests/performance-test/perf_updateInfo.py --headless
```

The `common/auth.py` module calls `load_env()` at import time, so you never need to set it manually in the script.

---

## Quick Reference

| Goal | Command |
|---|---|
| Measure auth flow SLA / leak detection | `locust -f pytests/performance-test/perf_authFlow.py --headless` |
| Measure `updateInfo` SLA | `locust -f pytests/performance-test/perf_updateInfo.py --headless` |
| Full user journey (write + read) | `locust -f pytests/performance-test/scenarios/user_journey.py --headless` |
| Baseline `userInfo` read load | `locust -f pytests/performance-test/perf_userInfo.py --headless -u 20 -r 5 --run-time 5m --class UserInfoUser` |
| Latency simulation (web UI class picker) | `locust -f pytests/performance-test/perf_userInfo.py --class-picker` |
| Concurrent burst (`userInfo`) | `locust -f pytests/performance-test/perf_userInfo.py --headless -u 5 -r 1 --run-time 5m --class ConcurrentRequestUser` |
| Auth-variation / bad-token behaviour | `locust -f pytests/performance-test/perf_userInfo.py --headless -u 10 -r 2 --run-time 5m --class ParameterVariationUser` |
| 2-hour soak (`userInfo`) | `locust -f pytests/performance-test/perf_userInfo.py --headless -u 20 -r 2 --run-time 2h --class UserInfoUser` |
| 3-hour soak (auth cycle) | swap `StagesShape` → `SoakShape` in `perf_authFlow.py`, then `locust -f pytests/performance-test/perf_authFlow.py --headless --run-time 3h` |
| Open web UI (any script) | Remove `--headless` from any command above |
