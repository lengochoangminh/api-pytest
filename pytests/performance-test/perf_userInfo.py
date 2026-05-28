import os
import sys
import time
import random

from gevent.pool import Pool
from locust import User, HttpUser, task, between, constant

# ---------------------------------------------------------------------------
# sys.path: project root (api/, config.py) + performance-test root (common/)
# ---------------------------------------------------------------------------
_PERF_ROOT    = os.path.abspath(os.path.dirname(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_PERF_ROOT, "..", ".."))
for _p in [_PROJECT_ROOT, _PERF_ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# common.auth handles load_env() — no need to call it here.
from common.auth import make_api_client, get_next_account
from config import API_BASE_URL
from api.unified_id_api import Unified_ID_API


# =============================================================================
# LATENCY SIMULATION USER
# =============================================================================

class LatencySimulationUser(User):
    """
    Simulates users on slow network connections.

    Adds artificial client-side delay before each GET /api/v1/user-info call
    to validate timeout handling and connection resilience.

    Configuration
    -------------
    Change latency_profile on the class (or subclass) to switch delay range:
        "slow_3g" : 500 – 2 000 ms
        "fast_3g" : 100 –   500 ms  (default)
        "4g"      :  50 –   150 ms
        "wifi"    :  10 –    50 ms

    Example
    -------
        locust -f pytests/performance-test/locust_users.py \\
               --class-picker --headless -u 20 -r 2 --run-time 10m
    """

    wait_time = between(1, 3)

    latency_profile = "fast_3g"
    _latency_profiles = {
        "slow_3g": (500, 2000),
        "fast_3g": (100, 500),
        "4g":      (50,  150),
        "wifi":    (10,  50),
    }

    # ------------------------------------------------------------------ setup

    def on_start(self):
        self._uid = None
        try:
            self._uid = make_api_client(
                fire_event_fn=self.environment.events.request.fire
            )
        except Exception:
            return

    def on_stop(self):
        if self._uid:
            self._uid.close()

    # ---------------------------------------------------------------- helpers

    def _simulate_latency(self):
        min_ms, max_ms = self._latency_profiles.get(self.latency_profile, (100, 500))
        time.sleep(random.randint(min_ms, max_ms) / 1000.0)

    def _fire(self, name: str, start: float, response, exc=None):
        elapsed_ms = (time.perf_counter() - start) * 1_000
        length = len(response.content) if response is not None else 0
        if exc is None and response is not None:
            try:
                body = response.json()
                if body.get("errorCode") != 0:
                    exc = Exception(
                        f"errorCode={body.get('errorCode')} message={body.get('message')}"
                    )
            except Exception as e:
                exc = e
        self.environment.events.request.fire(
            request_type="GET",
            name=name,
            response_time=elapsed_ms,
            response_length=length,
            exception=exc,
            context={},
        )

    # ------------------------------------------------------------------ tasks

    @task
    def get_user_info_with_latency(self):
        """GET /api/v1/user-info after simulated network delay."""
        if not self._uid:
            return

        self._simulate_latency()

        start = time.perf_counter()
        response = exc = None
        try:
            response = self._uid.get_user_info()
            if response.status_code != 200:
                exc = Exception(f"HTTP {response.status_code}")
        except Exception as e:
            exc = e

        self._fire(
            name=f"GET /api/v1/user-info (latency:{self.latency_profile})",
            start=start,
            response=response,
            exc=exc,
        )


# =============================================================================
# USER INFO USER  (replaces StressTestUser + SoakTestUser)
# =============================================================================

class UserInfoUser(User):
    """
    Minimal GET /api/v1/user-info user with periodic per-user logging.

    The load level (stress vs soak) is controlled entirely by the shape or
    the -u/-r/--run-time CLI flags — not by this class.

    Examples
    --------
    Stress ramp (20 users, 5-minute run):
        locust -f pytests/performance-test/locust_users.py \\
               --headless -u 20 -r 5 --run-time 5m

    2-hour soak (20 users, moderate pace):
        locust -f pytests/performance-test/locust_users.py \\
               --headless -u 20 -r 2 --run-time 2h
    """

    wait_time = between(1, 3)
    log_interval = 100  # print a per-user summary every N requests

    # ------------------------------------------------------------------ setup

    def on_start(self):
        self._uid = None
        try:
            self._uid = make_api_client(
                fire_event_fn=self.environment.events.request.fire
            )
        except Exception:
            return
        self._request_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._start_time    = time.time()

    def on_stop(self):
        if self._uid:
            self._uid.close()

    # ---------------------------------------------------------------- helpers

    def _fire(self, name: str, start: float, response, exc=None):
        elapsed_ms = (time.perf_counter() - start) * 1_000
        length = len(response.content) if response is not None else 0
        if exc is None and response is not None:
            try:
                body = response.json()
                if body.get("errorCode") != 0:
                    exc = Exception(
                        f"errorCode={body.get('errorCode')} message={body.get('message')}"
                    )
            except Exception as e:
                exc = e
        self.environment.events.request.fire(
            request_type="GET",
            name=name,
            response_time=elapsed_ms,
            response_length=length,
            exception=exc,
            context={},
        )

    # ------------------------------------------------------------------ tasks

    @task
    def get_user_info(self):
        """GET /api/v1/user-info with periodic per-user stats logging."""
        if not self._uid:
            return

        self._request_count += 1
        start = time.perf_counter()
        response = exc = None
        try:
            response = self._uid.get_user_info()
            if response.status_code != 200:
                exc = Exception(f"HTTP {response.status_code}")
                self._failure_count += 1
            else:
                self._success_count += 1
        except Exception as e:
            exc = e
            self._failure_count += 1

        self._fire("GET /api/v1/user-info", start, response, exc)

        if self._request_count % self.log_interval == 0:
            elapsed = time.time() - self._start_time
            rate = self._request_count / elapsed if elapsed > 0 else 0
            pct  = self._success_count / self._request_count * 100
            print(
                f"[UserInfoUser] reqs={self._request_count} "
                f"success={pct:.1f}% rate={rate:.2f}/s "
                f"uptime={elapsed / 60:.1f}min"
            )


# =============================================================================
# PARAMETER VARIATION USER
# =============================================================================

class ParameterVariationUser(HttpUser):
    """
    Tests API with various parameter combinations.

    This user class makes requests with different parameter types:
    - Valid requests: Standard authenticated calls (weight: 5)
    - Invalid token: Malformed/expired tokens (weight: 2)
    - Missing auth: No Authorization header (weight: 1)
    - Empty token: Empty bearer token (weight: 1)

    Use this to test:
    - Error handling for invalid inputs
    - Security of authentication checks
    - Response codes for different scenarios
    - Edge case handling

    Expected responses:
    - valid_request: 200 OK
    - invalid_token: 401 Unauthorized
    - missing_auth: 401 Unauthorized
    - empty_token: 401 Unauthorized

    Example:
        locust -f locust_file.py,locust_users.py ParameterVariationUser --headless -u 10 -r 2 --run-time 5m
    """

    host = API_BASE_URL()
    wait_time = between(1, 2)

    def on_start(self):
        """Authenticate once and point self.client at the dynamic service URL."""
        account = get_next_account()
        api = Unified_ID_API(account["email"], pwd=account["pwd"])
        self.client.base_url = api.service_url
        self.bearer_token = f"Bearer {api.access_token}"
        self.valid_headers = {
            "Content-Type": "application/json",
            "Authorization": self.bearer_token,
        }
        api.close()

    @task(5)
    def valid_request(self):
        """
        Make a valid authenticated request.

        This represents normal user behavior with proper authentication.
        Expected: 200 OK with user info response.
        """
        with self.client.get(
            "/api/v1/user-info",
            headers=self.valid_headers,
            name="GET /api/v1/user-info [valid]",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"Expected 200, got {response.status_code}")
            else:
                response.success()

    @task(2)
    def invalid_token(self):
        """
        Make request with invalid/malformed token.

        Tests API handling of malformed authentication tokens.
        Expected: 401 Unauthorized.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer invalid_token_12345_malformed",
        }

        with self.client.get(
            "/api/v1/user-info",
            headers=headers,
            name="GET /api/v1/user-info [invalid_token]",
            catch_response=True,
        ) as response:
            # We expect 401 for invalid token
            if response.status_code == 401:
                response.success()
            elif response.status_code == 200:
                response.failure("Security issue: Invalid token accepted")
            else:
                # Other status codes are acceptable error responses
                response.success()

    @task(1)
    def missing_auth(self):
        """
        Make request without Authorization header.

        Tests API handling when authentication is completely missing.
        Expected: 401 Unauthorized.
        """
        headers = {
            "Content-Type": "application/json",
            # No Authorization header
        }

        with self.client.get(
            "/api/v1/user-info",
            headers=headers,
            name="GET /api/v1/user-info [missing_auth]",
            catch_response=True,
        ) as response:
            # We expect 401 for missing auth
            if response.status_code == 401:
                response.success()
            elif response.status_code == 200:
                response.failure("Security issue: Missing auth accepted")
            else:
                response.success()

    @task(1)
    def empty_token(self):
        """
        Make request with empty bearer token.

        Tests API handling of empty authentication value.
        Expected: 401 Unauthorized.
        """
        headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer ",
        }

        with self.client.get(
            "/api/v1/user-info",
            headers=headers,
            name="GET /api/v1/user-info [empty_token]",
            catch_response=True,
        ) as response:
            if response.status_code == 401:
                response.success()
            elif response.status_code == 200:
                response.failure("Security issue: Empty token accepted")
            else:
                response.success()


# =============================================================================
# CONCURRENT REQUEST USER
# =============================================================================

class ConcurrentRequestUser(HttpUser):
    """
    Sends parallel burst requests to test concurrent handling.

    This user class sends multiple simultaneous requests using gevent pools,
    useful for testing:
    - Connection pool behavior
    - Concurrent request handling
    - Response time variance under burst load
    - Server thread pool capacity

    Configuration:
        concurrent_requests: Number of parallel requests per burst (default: 10)
        burst_interval: Time between bursts in seconds (default: 5)

    Each burst sends 10 parallel requests and measures:
    - Total batch time
    - Individual response times
    - Success/failure counts

    Example:
        locust -f locust_file.py,locust_users.py ConcurrentRequestUser --headless -u 5 -r 1 --run-time 5m
    """

    host = API_BASE_URL()
    wait_time = constant(5)  # Wait between bursts

    # Configuration
    concurrent_requests = 10  # Requests per burst

    def on_start(self):
        """Authenticate once and point self.client at the dynamic service URL."""
        account = get_next_account()
        api = Unified_ID_API(account["email"], pwd=account["pwd"])
        self.client.base_url = api.service_url
        self.bearer_token = f"Bearer {api.access_token}"
        self.common_headers = {
            "Content-Type": "application/json",
            "Authorization": self.bearer_token,
        }
        api.close()
        self._burst_count = 0

    def _make_single_request(self):
        """Make a single request and return timing info."""
        start = time.time()
        try:
            response = self.client.get(
                "/api/v1/user-info",
                headers=self.common_headers,
                name="GET /api/v1/user-info [concurrent]",
            )
            elapsed = (time.time() - start) * 1000
            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_time_ms": elapsed,
            }
        except Exception as e:
            elapsed = (time.time() - start) * 1000
            return {
                "success": False,
                "status_code": None,
                "response_time_ms": elapsed,
                "error": str(e),
            }

    @task
    def concurrent_burst(self):
        """
        Send multiple concurrent requests and analyze results.

        Uses gevent Pool to send parallel requests, then aggregates
        timing and success metrics for the burst.
        """
        self._burst_count += 1
        batch_start = time.time()

        # Create pool and spawn concurrent requests
        pool = Pool(self.concurrent_requests)
        results = pool.map(lambda _: self._make_single_request(), range(self.concurrent_requests))

        batch_elapsed = (time.time() - batch_start) * 1000

        # Analyze results
        successes = sum(1 for r in results if r["success"])
        failures = self.concurrent_requests - successes
        response_times = [r["response_time_ms"] for r in results]
        avg_time = sum(response_times) / len(response_times)
        min_time = min(response_times)
        max_time = max(response_times)

        # Log burst statistics
        print(f"[CONCURRENT] Burst #{self._burst_count}: {successes}/{self.concurrent_requests} success, "
              f"avg={avg_time:.1f}ms, min={min_time:.1f}ms, max={max_time:.1f}ms, "
              f"batch={batch_elapsed:.1f}ms")
