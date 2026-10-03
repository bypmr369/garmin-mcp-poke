"""
Garmin Connect authentication wrapper for cloud deployment.

Uses garminconnect >= 0.3 (native login, no garth). Login is deferred to the
first tool call so a failed login cannot crash the server at startup.
"""
import base64
import json
import os
import sys
import time

from garminconnect import Garmin

from config import GARMINTOKENS_BASE64, GARMIN_EMAIL, GARMIN_PASSWORD

RETRY_COOLDOWN_SECONDS = 900  # wait 15 minutes after a failed login
TOKEN_DIR = "/tmp/garminconnect"
TOKEN_FILE = os.path.join(TOKEN_DIR, "garmin_tokens.json")


class LazyGarmin:
    """Stands in for the Garmin client; logs in on first use, backs off on failure."""

    def __init__(self, factory, cooldown=RETRY_COOLDOWN_SECONDS):
        self._factory = factory
        self._cooldown = cooldown
        self._client = None
        self._next_try = 0.0

    def _get(self):
        if self._client is not None:
            return self._client
        wait = self._next_try - time.time()
        if wait > 0:
            raise RuntimeError(
                f"Garmin login failed recently; retrying in {int(wait)}s."
            )
        try:
            client = self._factory()
        except Exception as e:
            self._next_try = time.time() + self._cooldown
            print(f"ERROR: Garmin login failed: {e}", file=sys.stderr)
            raise RuntimeError(f"Garmin login failed: {e}") from e
        if client is None:
            self._next_try = time.time() + self._cooldown
            raise RuntimeError("Garmin login failed; see server log.")
        self._client = client
        return client

    def __getattr__(self, name):
        if name.startswith("_"):
            raise AttributeError(name)
        return getattr(self._get(), name)


def init_garmin_client():
    """Return a Garmin client that authenticates on first use.

    Authentication priority:
    1. GARMINTOKENS_BASE64 env var (base64 of garmin_tokens.json)
    2. GARMIN_EMAIL + GARMIN_PASSWORD (only works without MFA)

    Returns:
        A LazyGarmin wrapper, or None if no credentials are configured.
    """
    if GARMINTOKENS_BASE64:
        return LazyGarmin(lambda: _auth_with_tokens(GARMINTOKENS_BASE64))

    if GARMIN_EMAIL and GARMIN_PASSWORD:
        return LazyGarmin(lambda: _auth_with_credentials(GARMIN_EMAIL, GARMIN_PASSWORD))

    print(
        "ERROR: No Garmin credentials configured.\n"
        "Set GARMINTOKENS_BASE64 (recommended) or GARMIN_EMAIL + GARMIN_PASSWORD.",
        file=sys.stderr,
    )
    return None


def _auth_with_tokens(token_value: str):
    """Authenticate from GARMINTOKENS_BASE64 (base64 of garmin_tokens.json)."""
    raw = token_value.strip()
    try:
        token_json = raw if raw.startswith("{") else base64.b64decode(raw).decode("utf-8")
        parsed = json.loads(token_json)
    except Exception as e:
        print(f"ERROR: GARMINTOKENS_BASE64 could not be decoded: {e}", file=sys.stderr)
        return None
    if not isinstance(parsed, dict):
        print(
            "ERROR: GARMINTOKENS_BASE64 is in the old garth format. "
            "Generate a new garmin_tokens.json and set its base64 instead.",
            file=sys.stderr,
        )
        return None

    # Keep a token file for this instance so refreshed tokens are reused.
    os.makedirs(TOKEN_DIR, mode=0o700, exist_ok=True)
    if not os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "w") as f:
            f.write(token_json)
        os.chmod(TOKEN_FILE, 0o600)

    garmin = Garmin()
    garmin.login(TOKEN_DIR)
    print("Garmin client authenticated via tokens.", file=sys.stderr)
    return garmin


def _auth_with_credentials(email: str, password: str):
    """Authenticate using email and password (no MFA support in cloud)."""
    garmin = Garmin(email=email, password=password)
    garmin.login()
    print("Garmin client authenticated via credentials.", file=sys.stderr)
    return garmin
