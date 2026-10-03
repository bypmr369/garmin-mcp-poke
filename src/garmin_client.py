"""
Garmin Connect authentication wrapper for cloud deployment.

Handles token-based and credential-based authentication for the Garmin API.
Login is deferred to the first tool call so a rate-limited login (HTTP 429)
cannot crash the server at startup.
"""
import io
import sys
import time

from garminconnect import Garmin, GarminConnectAuthenticationError
from garth.exc import GarthHTTPError

from config import GARMINTOKENS_BASE64, GARMIN_EMAIL, GARMIN_PASSWORD

RETRY_COOLDOWN_SECONDS = 900  # wait 15 minutes after a failed login


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
    1. GARMINTOKENS_BASE64 env var (base64-encoded OAuth tokens, recommended for cloud)
    2. GARMIN_EMAIL + GARMIN_PASSWORD (direct credentials, only works without MFA)

    Returns:
        A LazyGarmin wrapper, or None if no credentials are configured.
    """
    if GARMINTOKENS_BASE64:
        return LazyGarmin(lambda: _auth_with_tokens(GARMINTOKENS_BASE64))

    if GARMIN_EMAIL and GARMIN_PASSWORD:
        return LazyGarmin(lambda: _auth_with_credentials(GARMIN_EMAIL, GARMIN_PASSWORD))

    print(
        "ERROR: No Garmin credentials configured.\n"
        "Set GARMINTOKENS_BASE64 (recommended) or GARMIN_EMAIL + GARMIN_PASSWORD.\n"
        "Run 'python scripts/generate_tokens.py' to generate tokens.",
        file=sys.stderr,
    )
    return None


def _auth_with_tokens(token_base64: str):
    """Authenticate using base64-encoded OAuth tokens."""
    # Suppress garth stderr noise during token validation
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()

    try:
        garmin = Garmin()
        garmin.login(token_base64)
    except (FileNotFoundError, GarthHTTPError, GarminConnectAuthenticationError) as e:
        sys.stderr = old_stderr
        print(f"ERROR: Token authentication failed: {e}", file=sys.stderr)
        print(
            "Tokens may be expired. Re-run 'python scripts/generate_tokens.py' to refresh.",
            file=sys.stderr,
        )
        return None
    finally:
        sys.stderr = old_stderr

    print("Garmin client authenticated via tokens.", file=sys.stderr)
    return garmin


def _auth_with_credentials(email: str, password: str):
    """Authenticate using email and password (no MFA support in cloud)."""
    try:
        garmin = Garmin(email=email, password=password, is_cn=False)
        garmin.login()
    except (GarthHTTPError, GarminConnectAuthenticationError) as e:
        print(f"ERROR: Credential authentication failed: {e}", file=sys.stderr)
        print(
            "If your account has MFA, use GARMINTOKENS_BASE64 instead.",
            file=sys.stderr,
        )
        return None

    print("Garmin client authenticated via credentials.", file=sys.stderr)
    return garmin
