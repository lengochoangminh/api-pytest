"""
Performance Test: Authentication Flow
======================================
Covers the complete 3-step OAuth authentication flow:

  Step 1 — POST /api/v1/login             (credentials → serviceUrl + redirectParams)
  Step 2 — GET  {serviceUrl}/oauth/authorize   (OAuth redirect → location header)
  Step 3 — POST {serviceUrl}/api/v1/token      (token exchange → accessToken)

Each step is measured individually so bottlenecks within the flow are visible.
A composite "full cycle" event is also fired for end-to-end latency tracking.

Memory leak focus
-----------------
A fresh httpx.Client is created AND explicitly closed after every task iteration.
This directly probes whether connections, token strings, or response objects
accumulate across repeated auth cycles — the #1 suspected leak source based on
code review of unified_id_api.py.

  If RSS memory grows monotonically across iterations → client connections are
  leaking (OS-level TCP sockets not released).

  If RSS is flat but Python heap grows → token string objects are accumulating
  in Python references after .close() (use tracemalloc to confirm).

Test types supported (swap shape import below):
  StagesShape — 8-min staged ramp          (load + stress, default)
  SoakShape   — flat 20-user sustained run  (memory leak detection, --run-time 3h)
  SpikeShape  — sudden burst to 200 users   (auth stampede simulation)

Load shape (StagesShape — default):
  Stage 1  :   0 –  60 s |  5 users | spawn  1/s  – warm-up
  Stage 2  :  60 – 180 s | 20 users | spawn  2/s  – baseline load
  Stage 3  : 180 – 300 s | 50 users | spawn  5/s  – stress ramp
  Stage 4  : 300 – 420 s | 50 users | spawn  5/s  – sustained peak
  Stage 5  : 420 – 480 s |  0 users | spawn 10/s  – ramp-down / stop

Success criteria:
  - HTTP 200 on login (Step 1) and token exchange (Step 3)
  - HTTP 302/307 on OAuth authorize (Step 2)
  - errorCode == 0 in login and token JSON responses (failures counted as Locust errors)
  - p95 < 5 000 ms  (full auth cycle — 3-hop round trip is inherently slower)
  - p99 < 10 000 ms
  - Failure rate < 1 %

Run commands
------------
  # Default — 8-min staged ramp, web UI at http://localhost:8089
  locust -f pytests/performance-test/perf_authFlow.py

  # Headless (shape drives users & duration automatically)
  locust -f pytests/performance-test/perf_authFlow.py --headless

  # Soak — swap StagesShape → SoakShape in the import below, then:
  locust -f pytests/performance-test/perf_authFlow.py --headless --run-time 3h

  # Spike — swap StagesShape → SpikeShape in the import below, then:
  locust -f pytests/performance-test/perf_authFlow.py --headless
"""

import os
import sys
import time
import random
import uuid
import httpx

from locust import User, task, between

# ---------------------------------------------------------------------------
# sys.path: project root (api/, config.py) + performance-test root (common/)
# ---------------------------------------------------------------------------
_PERF_ROOT    = os.path.abspath(os.path.dirname(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_PERF_ROOT, "..", ".."))
for _p in [_PROJECT_ROOT, _PERF_ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# common.auth handles load_env() — no need to call it here.
from common.auth import get_next_account
from common.shapes import StagesShape  # noqa: F401  swap to SoakShape or SpikeShape as needed
from config import API_BASE_URL
from utilities.helpers import Helpers


# ---------------------------------------------------------------------------
# AuthFlowUser
# ---------------------------------------------------------------------------

class AuthFlowUser(User):
    """
    Virtual user that performs the complete 3-step OAuth auth cycle per task.

    Unlike other VU classes, this user does NOT hold a persistent API client.
    Instead, every task iteration:
      1. Creates a fresh httpx.Client
      2. Executes login → OAuth redirect → token exchange
      3. Explicitly calls client.close() in a finally block

    This pattern maximises leak detection: if connections are not properly
    released by httpx after close(), the OS TCP connection count and Python
    heap will grow with each iteration.

    Lifecycle
    ---------
    on_start  – resolve credentials for this VU (no HTTP call)
    tasks     – one task: full auth cycle with per-step timing
    on_stop   – nothing persistent to clean up
    """

    # Think time: 2–5 s between auth attempts (simulates re-login / session expiry)
    wait_time = between(2, 5)

    # ------------------------------------------------------------------ setup

    def on_start(self):
        """Resolve pooled credentials for this VU. No HTTP calls yet."""
        self._account = get_next_account()

    def on_stop(self):
        pass  # No persistent client to close

    # ---------------------------------------------------------------- helpers

    def _fire(
        self,
        request_type: str,
        name: str,
        start: float,
        response,
        exc=None,
        check_json: bool = True,
    ):
        """
        Emit a Locust request event.

        Args:
            request_type: HTTP method string shown in Locust UI (POST, GET, AUTH)
            name:         Endpoint label shown in Locust UI
            start:        perf_counter() timestamp from before the call
            response:     httpx.Response or None on network failure
            exc:          Pre-set exception (e.g. unexpected HTTP status).
                          When None and check_json=True, also validates errorCode.
            check_json:   Set False for responses that are not JSON (e.g. OAuth
                          302 redirect). Prevents spurious JSON parse failures.
        """
        elapsed_ms = (time.perf_counter() - start) * 1_000
        length = len(response.content) if response is not None else 0

        if exc is None and check_json and response is not None:
            try:
                body = response.json()
                if body.get("errorCode") != 0:
                    exc = Exception(
                        f"errorCode={body.get('errorCode')} message={body.get('message')}"
                    )
            except Exception as parse_exc:
                exc = parse_exc

        self.environment.events.request.fire(
            request_type=request_type,
            name=name,
            response_time=elapsed_ms,
            response_length=length,
            exception=exc,
            context={},
        )

    # ------------------------------------------------------------------ tasks

    @task
    def full_auth_cycle(self):
        """
        Execute the complete 3-step OAuth flow and time each step individually.

        A fresh httpx.Client is created at the start and closed in the finally
        block regardless of success or failure — this is the connection leak probe.
        """
        email    = self._account["email"]
        pwd      = self._account["pwd"]
        base_url = API_BASE_URL()

        client      = httpx.Client(timeout=30.0)
        cycle_start = time.perf_counter()
        exc_cycle   = None

        try:
            # ── Step 1: POST /api/v1/login ────────────────────────────────────
            # Goal: obtain serviceUrl + redirectParams for the OAuth flow.
            login_headers = {
                "Content-Type": "application/json",
                "session_code": Helpers.generate_session_code(),
                "Accept": "application/json, text/plain, */*",
                "X-Requested-With": "XMLHttpRequest",
                "Cache-Control": "no-cache",
                "X-Request-ID": f"perf-{int(time.time() * 1000)}-{random.randint(1000, 9999)}",
                "X-Client-Session": f"session-{uuid.uuid4().hex[:16]}",
                "Connection": "keep-alive",
            }
            login_payload = {
                "email": email,
                "password": pwd,
                "terminalUUID": Helpers.generate_UUID(),
            }

            step1_start    = time.perf_counter()
            step1_response = None
            step1_exc      = None
            try:
                step1_response = client.post(
                    f"{base_url}/api/v1/login",
                    json=login_payload,
                    headers=login_headers,
                )
                if step1_response.status_code != 200:
                    step1_exc = Exception(f"HTTP {step1_response.status_code}")
            except Exception as e:
                step1_exc = e

            self._fire("POST", "POST /api/v1/login", step1_start, step1_response, step1_exc)

            if step1_exc or step1_response is None:
                exc_cycle = step1_exc
                return

            login_data      = step1_response.json()
            service_url     = login_data.get("result", {}).get("serviceUrl")
            redirect_params = login_data.get("result", {}).get("redirectParams")

            if not service_url or not redirect_params:
                exc_cycle = Exception("Missing serviceUrl or redirectParams in login response")
                return

            # ── Step 2: GET {serviceUrl}/oauth/authorize ──────────────────────
            # Goal: follow the OAuth redirect to obtain the token code in the
            # Location header. Response is 302/307 — not JSON.
            oauth_url = f"{service_url}/oauth/authorize?{redirect_params}&language=en_US"
            oauth_headers = {
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.6",
                "Connection": "keep-alive",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/138.0.0.0 Safari/537.36"
                ),
                "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Brave";v="138"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"macOS"',
            }

            step2_start    = time.perf_counter()
            step2_response = None
            step2_exc      = None
            token_params   = None
            try:
                step2_response = client.get(
                    oauth_url, headers=oauth_headers, follow_redirects=False
                )
                if step2_response.status_code not in (302, 307):
                    step2_exc = Exception(
                        f"Expected 302/307, got HTTP {step2_response.status_code}"
                    )
                else:
                    location = step2_response.headers.get("location", "")
                    if "#/token?" not in location:
                        step2_exc = Exception(
                            f"Invalid OAuth redirect — missing #/token? in Location header"
                        )
                    else:
                        token_params = location.split("#/token?")[1].split("&serviceUrl=")[0]
            except Exception as e:
                step2_exc = e

            # check_json=False: OAuth redirect returns HTML, not a JSON body
            self._fire(
                "GET",
                "GET /oauth/authorize",
                step2_start,
                step2_response,
                step2_exc,
                check_json=False,
            )

            if step2_exc or token_params is None:
                exc_cycle = step2_exc
                return

            # ── Step 3: POST {serviceUrl}/api/v1/token ────────────────────────
            # Goal: exchange the OAuth code for accessToken + refreshToken.
            token_url     = f"{service_url}/api/v1/token?{token_params}"
            token_headers = {
                "Accept": "application/json, text/plain, */*",
                "Accept-Language": "en-US,en;q=0.6",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Content-Length": "0",
                "User-Agent": oauth_headers["User-Agent"],
                "X-Requested-With": "XMLHttpRequest",
                "sec-ch-ua": oauth_headers["sec-ch-ua"],
                "sec-ch-ua-mobile": oauth_headers["sec-ch-ua-mobile"],
                "sec-ch-ua-platform": oauth_headers["sec-ch-ua-platform"],
            }

            step3_start    = time.perf_counter()
            step3_response = None
            step3_exc      = None
            try:
                step3_response = client.post(token_url, data={}, headers=token_headers)
                if step3_response.status_code != 200:
                    step3_exc = Exception(f"HTTP {step3_response.status_code}")
            except Exception as e:
                step3_exc = e

            self._fire("POST", "POST /api/v1/token", step3_start, step3_response, step3_exc)

            if step3_exc:
                exc_cycle = step3_exc

        except Exception as e:
            exc_cycle = e

        finally:
            # ── Always close the client — this is the connection leak probe ───
            # If OS TCP connections keep growing across iterations, close() is
            # not releasing the underlying socket pool properly.
            client.close()

        # ── Composite event: full auth round-trip ─────────────────────────────
        # Reported as "AUTH" type in the Locust UI for easy filtering.
        cycle_elapsed_ms = (time.perf_counter() - cycle_start) * 1_000
        self.environment.events.request.fire(
            request_type="AUTH",
            name="AUTH /api/v1 full cycle (login → oauth → token)",
            response_time=cycle_elapsed_ms,
            response_length=0,
            exception=exc_cycle,
            context={},
        )
