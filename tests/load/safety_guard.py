"""
PlantProof Load Testing Safety Guard
Enforces strict local target verification and prevents accidental load testing
against public, production, or third-party regulator endpoints.
"""

import os
import sys
import urllib.parse
from typing import Optional


class LoadTestSafetyViolation(Exception):
    """Raised when an unsafe or non-local load test target is detected."""
    pass


ALLOWED_LOCAL_HOSTS = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "testserver",
}


def validate_load_test_target(target_url: str) -> bool:
    """
    Validates that the target URL is strictly local.
    Rejects any non-local hostname unless ALLOW_NONLOCAL_LOAD_TESTS is explicitly
    set to 'true' (defaults to 'false'; must never be set automatically).
    """
    if not target_url:
        raise LoadTestSafetyViolation("No target URL specified for load testing.")

    parsed = urllib.parse.urlparse(target_url)
    hostname = (parsed.hostname or "").lower()

    # Reject cloud, public, and external regulator websites unconditionally
    prohibited_keywords = [
        "gov.in", "nic.in", "mpcb", "cpcb", "moef", "peso", "dish",
        "aws", "amazon", "google", "gcp", "azure", "heroku", "render",
        ".com", ".org", ".net", ".io"
    ]
    for kw in prohibited_keywords:
        if kw in hostname and hostname not in ALLOWED_LOCAL_HOSTS:
            raise LoadTestSafetyViolation(
                f"SAFETY VIOLATION: Target '{target_url}' contains prohibited external keyword '{kw}'. "
                "Load testing against public or government infrastructure is strictly illegal and prohibited."
            )

    is_local = hostname in ALLOWED_LOCAL_HOSTS

    allow_nonlocal = os.environ.get("ALLOW_NONLOCAL_LOAD_TESTS", "false").lower() == "true"

    if not is_local and not allow_nonlocal:
        raise LoadTestSafetyViolation(
            f"SAFETY VIOLATION: Target host '{hostname}' is not a permitted local target ({ALLOWED_LOCAL_HOSTS}). "
            "Load tests can only target local instances. "
            "To override (FOR AUTHORIZED ISOLATED STAGING ONLY), you must manually export ALLOW_NONLOCAL_LOAD_TESTS=true."
        )

    return True


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    try:
        validate_load_test_target(target)
        print(f"Safety Check Passed: '{target}' is a verified safe local target.")
    except LoadTestSafetyViolation as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        sys.exit(1)
