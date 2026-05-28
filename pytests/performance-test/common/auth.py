"""
Shared authentication helpers for all performance test scripts.

Provides
--------
get_next_account()  – thread-safe cyclic credential pool
make_api_client()   – authenticate and return a ready Unified_ID_API instance

Calling load_env() is handled here at import time, so importing scripts do
NOT need to call it separately.
"""

import os
import sys
from itertools import cycle
from gevent.lock import Semaphore

# ---------------------------------------------------------------------------
# Project root on sys.path so api/ and config.py are importable from anywhere.
# common/auth.py lives at pytests/performance-test/common/, so root is 3 levels up.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from api.unified_id_api import Unified_ID_API
from config import (
    UID_USER_NAME,
    UID_PWD,
    ORG_OWNER_EMAIL,
    ORG_ADMIN_EMAIL,
    ORG_ADMIN_EMAIL_2,
    ORG_MEMBER_EMAIL,
    load_env,
)

# Load env once when this module is imported.
load_env(os.getenv("env", "beta_use1"))


# ---------------------------------------------------------------------------
# Credential pool
# ---------------------------------------------------------------------------

def _build_pool() -> list:
    pwd = UID_PWD()
    pool = [
        {"email": fn(), "pwd": pwd}
        for fn in [UID_USER_NAME, ORG_OWNER_EMAIL, ORG_ADMIN_EMAIL, ORG_ADMIN_EMAIL_2, ORG_MEMBER_EMAIL]
        if fn()
    ]
    return pool or [{"email": UID_USER_NAME(), "pwd": pwd}]


_pool = _build_pool()
_cycle = cycle(_pool)
_lock = Semaphore()


def get_next_account() -> dict:
    """Return the next {email, pwd} dict, cycling safely across greenlets."""
    with _lock:
        return next(_cycle)


# ---------------------------------------------------------------------------
# Auth factory
# ---------------------------------------------------------------------------

def make_api_client(fire_event_fn=None) -> Unified_ID_API:
    """
    Authenticate using the next pooled account and return a Unified_ID_API instance.

    The caller is responsible for calling .close() when done (or using it as a
    context manager).

    Args:
        fire_event_fn: optional self.environment.events.request.fire — when
                       provided, auth failures are emitted as Locust error
                       events before re-raising the exception.
    """
    account = get_next_account()
    try:
        return Unified_ID_API(account["email"], pwd=account["pwd"])
    except Exception as exc:
        if fire_event_fn:
            fire_event_fn(
                request_type="AUTH",
                name="authenticate",
                response_time=0,
                response_length=0,
                exception=exc,
                context={},
            )
        raise
