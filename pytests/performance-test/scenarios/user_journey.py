"""
User Journey Performance Test
==============================
Simulates a realistic user session across two endpoints:

  Step A – POST /api/v1/account/updateInfo  (write profile)  weight 3
  Step B – GET  /api/v1/user-info           (read profile)   weight 1

The 3:1 write:read ratio makes this a write-heavy scenario that reveals
contention and caching behaviour that single-endpoint tests miss.

Default shape : StagesShape (8-minute staged ramp, self-terminating)
Swap the import below to use SoakShape or SpikeShape instead.

Run commands
------------
  # Default — 8-min staged ramp, web UI at http://localhost:8089
  locust -f pytests/performance-test/scenarios/user_journey.py

  # Headless (shape drives users & duration automatically)
  locust -f pytests/performance-test/scenarios/user_journey.py --headless

  # 2-hour soak (swap StagesShape → SoakShape in import below, then:)
  locust -f pytests/performance-test/scenarios/user_journey.py --headless --run-time 2h

  # Spike test (swap StagesShape → SpikeShape in import below)
  locust -f pytests/performance-test/scenarios/user_journey.py --headless

Success criteria
----------------
  - HTTP 200 on every request
  - errorCode == 0 in response body   (non-zero is counted as a Locust failure)
  - p95 < 2 000 ms
  - p99 < 5 000 ms
  - Failure rate < 1 %
"""

import os
import sys
import time
import random

from locust import User, task, between

# ---------------------------------------------------------------------------
# sys.path: project root (api/, config.py) + performance-test root (common/)
# ---------------------------------------------------------------------------
_PERF_ROOT    = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_PROJECT_ROOT = os.path.abspath(os.path.join(_PERF_ROOT, "..", ".."))
for _p in [_PROJECT_ROOT, _PERF_ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# common.auth also calls load_env() — no need to call it here.
from common.auth import make_api_client
from common.shapes import StagesShape  # swap to SoakShape or SpikeShape as needed  # noqa: F401

# ---------------------------------------------------------------------------
# Payload data pools
# ---------------------------------------------------------------------------
_FIRST_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank"]
_LAST_NAMES  = ["Smith", "Jones", "Lee", "Brown", "Davis", "Wilson", "Moore"]
_LANGUAGES   = ["en_US", "zh_TW", "zh_CN", "de_DE", "fr_FR"]


# ---------------------------------------------------------------------------
# User class
# ---------------------------------------------------------------------------

class UserJourneyUser(User):
    """
    Simulates a realistic user session: read profile → update profile.

    Lifecycle
    ---------
    on_start – authenticate once, snapshot original profile
    tasks    – alternating writes (weight 3) and reads (weight 1)
    on_stop  – restore original profile for test isolation, close client
    """

    wait_time = between(1, 3)

    # ------------------------------------------------------------------ setup

    def on_start(self):
        self._uid = None
        self._original: dict = {}
        self._account_id: str = ""
        self._email: str = ""

        try:
            self._uid = make_api_client(
                fire_event_fn=self.environment.events.request.fire
            )
        except Exception:
            return

        try:
            resp = self._uid.get_user_info()
            if resp.status_code == 200:
                result = resp.json().get("result", {})
                self._original  = result
                self._account_id = result.get("accountId", "")
                self._email      = result.get("email", "")
        except Exception:
            pass

    # ---------------------------------------------------------------- teardown

    def on_stop(self):
        if self._uid and self._original and self._account_id:
            try:
                self._uid.update_profile(
                    account_id=self._account_id,
                    email=self._email,
                    first_name=self._original.get("firstName"),
                    last_name=self._original.get("lastName"),
                    phone=self._original.get("phone"),
                    language=self._original.get("language"),
                    region=self._original.get("region"),
                    use24hour=self._original.get("use24hour"),
                )
            except Exception:
                pass
            finally:
                self._uid.close()

    # ------------------------------------------------------------------ tasks

    def _fire(self, method: str, name: str, start: float, response, exc=None):
        """Emit a Locust request event; marks errorCode != 0 as a failure."""
        elapsed_ms    = (time.perf_counter() - start) * 1_000
        response_length = len(response.content) if response is not None else 0

        if exc is None and response is not None:
            try:
                body = response.json()
                if body.get("errorCode") != 0:
                    exc = Exception(
                        f"errorCode={body.get('errorCode')} message={body.get('message')}"
                    )
            except Exception as parse_exc:
                exc = parse_exc

        self.environment.events.request.fire(
            request_type=method,
            name=name,
            response_time=elapsed_ms,
            response_length=response_length,
            exception=exc,
            context={},
        )

    @task(3)
    def update_profile(self):
        """POST /api/v1/account/updateInfo — full payload with randomised fields."""
        if not self._uid or not self._account_id:
            return

        start = time.perf_counter()
        response = exc = None
        try:
            response = self._uid.update_profile(
                account_id=self._account_id,
                email=self._email,
                first_name=random.choice(_FIRST_NAMES),
                last_name=random.choice(_LAST_NAMES),
                phone=f"{random.randint(100_000_0000, 999_999_9999)}",
                language=random.choice(_LANGUAGES),
                region=self._original.get("region", "MY"),
                use24hour=random.choice([True, False]),
            )
            if response.status_code != 200:
                exc = Exception(f"HTTP {response.status_code}")
        except Exception as e:
            exc = e

        self._fire("POST", "POST /api/v1/account/updateInfo", start, response, exc)

    @task(1)
    def get_user_info(self):
        """GET /api/v1/user-info — read the current profile."""
        if not self._uid:
            return

        start = time.perf_counter()
        response = exc = None
        try:
            response = self._uid.get_user_info()
            if response.status_code != 200:
                exc = Exception(f"HTTP {response.status_code}")
        except Exception as e:
            exc = e

        self._fire("GET", "GET /api/v1/user-info", start, response, exc)
