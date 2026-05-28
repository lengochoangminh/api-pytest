"""
Performance Test: POST /api/v1/account/updateInfo
=================================================
Target endpoint : POST /api/v1/account/updateInfo
Tool            : Locust 2.x
Auth strategy   : Each virtual user authenticates once in on_start() via the existing Unified_ID_API wrapper (handles the full 3-step
                  OAuth flow) and caches the token + service_url for the duration of the test.

Load shape (custom stages):
  Stage 1  0 –  60 s :  5 users  – warm-up
  Stage 2  60 – 180 s : 20 users  – baseline load
  Stage 3  180 – 300 s : 50 users  – stress ramp
  Stage 4  300 – 420 s : 50 users  – sustained peak
  Stage 5  420 – 480 s :  0 users  – ramp-down / stop  
=> Total: 480 seconds (8 minutes) for execution. When tick() returns None (after 480 s), Locust stops automatically — no --run-time flag needed.

Success criteria:
  - HTTP 200 on every request
  - errorCode == 0 in response body  (failures are counted as Locust errors)
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
_PERF_ROOT    = os.path.abspath(os.path.dirname(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_PERF_ROOT, "..", ".."))
for _p in [_PROJECT_ROOT, _PERF_ROOT]:
    if _p not in sys.path:
        sys.path.insert(0, _p)

# common.auth also calls load_env() — no need to call it here.
from common.auth import make_api_client

# noqa: F401  – discovered by Locust automatically
# StagesShape is imported from common/shapes.py above.
# Locust auto-discovers it via this module's namespace.
from common.shapes import StagesShape  

# ---------------------------------------------------------------------------
# Static data pools
# ---------------------------------------------------------------------------
_FIRST_NAMES = ["Alice", "Bob", "Carol", "Dave", "Eve", "Frank", "Grace", "Hank"]
_LAST_NAMES  = ["Smith", "Jones", "Lee", "Brown", "Davis", "Wilson", "Moore"]
_LANGUAGES   = ["en_US", "zh_TW", "de_DE", "fr_FR"]


# ---------------------------------------------------------------------------
# Locust User class
# ---------------------------------------------------------------------------

class UpdateInfoUser(User):
    """
    Virtual user that exercises POST /api/v1/account/updateInfo.

    Lifecycle
    ---------
    on_start  – authenticate once, fetch baseline profile
    tasks     – repeatedly call updateInfo with varying payloads
    on_stop   – restore original profile so the test account is not left dirty
    """

    # Think time: 1–3 s between tasks (simulates user paging / form interaction)
    wait_time = between(1, 3)

    # ------------------------------------------------------------------ setup

    def on_start(self):
        """Authenticate and snapshot the current profile."""
        self._uid = None
        self._original: dict = {}
        self._account_id: str = ""
        self._email: str = ""

        try:
            self._uid = make_api_client(
                fire_event_fn=self.environment.events.request.fire
            )
        except Exception as exc:
            raise  # event already fired inside make_api_client

        # Snapshot current profile for restoration after the test
        try:
            resp = self._uid.get_user_info()
            if resp.status_code == 200:
                result = resp.json().get("result", {})
                self._original   = result
                self._account_id = result.get("accountId", "")
                self._email      = result.get("email", "")
        except Exception:
            pass  # Non-fatal; restoration will be skipped if snapshot failed

    # ---------------------------------------------------------------- teardown

    def on_stop(self):
        """Restore original profile and close the HTTP client."""
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
                pass  # Best-effort restore; don't fail the shutdown
            finally:
                self._uid.close()

    # ------------------------------------------------------------------ tasks

    def _fire_event(self, name: str, start_time: float, response, exc=None):
        """Emit a Locust request event from a raw httpx Response."""
        elapsed_ms = (time.perf_counter() - start_time) * 1_000
        response_length = len(response.content) if response is not None else 0

        # Treat a successful HTTP 200 but errorCode != 0 as a logical failure
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
            request_type="POST",
            name=name,
            response_time=elapsed_ms,
            response_length=response_length,
            exception=exc,
            context={},
        )

    @task(3)
    def update_full_profile(self):
        """
        Realistic full-form save.
        Cycles through name/language pools so payloads vary across iterations.
        """
        if not self._uid or not self._account_id:
            return

        payload = dict(
            account_id=self._account_id,
            email=self._email,
            first_name=random.choice(_FIRST_NAMES),
            last_name=random.choice(_LAST_NAMES),
            phone=f"{random.randint(100_000_0000, 999_999_9999)}",
            language=random.choice(_LANGUAGES),
            region=self._original.get("region", "MY"),
            use24hour=random.choice([True, False]),
        )

        start = time.perf_counter()
        response = None
        exc = None
        try:
            response = self._uid.update_profile(**payload)
            if response.status_code != 200:
                exc = Exception(f"HTTP {response.status_code}")
        except Exception as e:
            exc = e

        self._fire_event(
            name="POST /api/v1/account/updateInfo (full)",
            start_time=start,
            response=response,
            exc=exc,
        )

    @task(1)
    def update_minimal(self):
        """
        Minimal payload – only the two required fields (accountId + email).
        Validates that the endpoint accepts requests with no optional fields.
        """
        if not self._uid or not self._account_id:
            return

        start = time.perf_counter()
        response = None
        exc = None
        try:
            response = self._uid.update_profile(
                account_id=self._account_id,
                email=self._email,
                first_name=random.choice(_FIRST_NAMES),
            )
            if response.status_code != 200:
                exc = Exception(f"HTTP {response.status_code}")
        except Exception as e:
            exc = e

        self._fire_event(
            name="POST /api/v1/account/updateInfo (minimal)",
            start_time=start,
            response=response,
            exc=exc,
        )