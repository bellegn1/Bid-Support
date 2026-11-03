"""
ServiceTitan API integration — DISABLED until API credentials are available.

To enable:
  1. Set SERVICETITAN_ENABLED = True
  2. Populate environment variables:
       SERVICETITAN_CLIENT_ID      — OAuth2 client ID from the ST developer portal
       SERVICETITAN_CLIENT_SECRET  — OAuth2 client secret
       SERVICETITAN_TENANT_ID      — the company's ServiceTitan tenant ID
  3. Implement the two TODOs below.

API reference: https://developer.servicetitan.io/apis/
Auth endpoint: https://auth.servicetitan.io/connect/token
Base URL:      https://api.servicetitan.io
"""

import os

SERVICETITAN_ENABLED = False  # Flip to True once creds are available


def _get_token() -> str:
    """Fetch short-lived OAuth2 bearer token from ServiceTitan auth server."""
    # TODO: POST to https://auth.servicetitan.io/connect/token with
    #   client_id, client_secret, grant_type=client_credentials, scope=...
    raise NotImplementedError("ServiceTitan OAuth2 not yet configured.")


def push_job_flag(job_data: dict) -> None:
    """
    Write flag result, benchmark range, and reason code back to a ServiceTitan
    estimate as custom fields.

    job_data keys expected:
      servicetitan_job_id, flag_status, benchmark_price, range_low, range_high,
      deviation_pct, expected_margin, reason_code, notes
    """
    if not SERVICETITAN_ENABLED:
        return

    token = _get_token()
    tenant = os.environ["SERVICETITAN_TENANT_ID"]
    job_id = job_data["servicetitan_job_id"]

    # TODO: PATCH https://api.servicetitan.io/jpm/v2/tenant/{tenant}/jobs/{job_id}
    #   with custom field payload containing flag_status, benchmark_price, reason_code
    raise NotImplementedError("ServiceTitan push not yet implemented.")


def fetch_job_context(job_id: str) -> dict | None:
    """
    Pull job type, property type, and estimated cost fields from an open
    ServiceTitan estimate to pre-fill the app form.

    Returns None when integration is disabled (app falls back to manual entry).
    """
    if not SERVICETITAN_ENABLED:
        return None

    token = _get_token()
    tenant = os.environ["SERVICETITAN_TENANT_ID"]

    # TODO: GET https://api.servicetitan.io/jpm/v2/tenant/{tenant}/jobs/{job_id}
    #   parse and return dict with keys: job_type, property_type, labor_cost,
    #   material_cost, po_cost, estimate_amount
    raise NotImplementedError("ServiceTitan fetch not yet implemented.")
