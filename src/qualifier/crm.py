"""HubSpot sink for qualified enquiries.

Runs in dry-run mode unless HUBSPOT_TOKEN is set, so the whole pipeline is
exercisable - and testable - without credentials or network access.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib import error, request

from .models import Decision, Enquiry

LOGGER = logging.getLogger(__name__)
HUBSPOT_CONTACTS_URL = "https://api.hubapi.com/crm/v3/objects/contacts"


def build_properties(enquiry: Enquiry, decision: Decision) -> dict[str, str]:
    """Map the call outcome onto HubSpot contact properties.

    Custom properties (funding_route, qualification_score, agent_handoff) must
    exist in the portal; see README for the property definitions.
    """
    first, _, last = (enquiry.full_name or "").partition(" ")
    return {
        "firstname": first,
        "lastname": last,
        "email": enquiry.email or "",
        "phone": enquiry.phone or "",
        "company": enquiry.company_name or "",
        "funding_route": ",".join(r.value for r in decision.routes),
        "qualification_score": str(decision.score),
        "agent_handoff": "true" if decision.handoff else "false",
        "hs_lead_status": "OPEN" if decision.handoff else "NEW",
    }


def push_contact(
    enquiry: Enquiry, decision: Decision, token: str | None = None, timeout: float = 10.0
) -> dict[str, Any]:
    """Create the contact in HubSpot, or describe what would be sent.

    Never raises on a CRM failure: losing a lead is bad, dropping the call
    because the CRM is down is worse. The caller decides what to do with
    the returned status.
    """
    token = token or os.getenv("HUBSPOT_TOKEN")
    properties = build_properties(enquiry, decision)

    if not token:
        LOGGER.info("HUBSPOT_TOKEN unset - dry run, no contact created")
        return {"status": "dry_run", "properties": properties}

    payload = json.dumps({"properties": properties}).encode()
    req = request.Request(
        HUBSPOT_CONTACTS_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=timeout) as response:
            body = json.loads(response.read().decode())
        return {"status": "created", "id": body.get("id")}
    except error.HTTPError as exc:  # pragma: no cover - needs a live portal
        LOGGER.warning("HubSpot rejected the contact: %s", exc.code)
        return {"status": "error", "code": exc.code}
    except Exception as exc:  # pragma: no cover - network failure path
        LOGGER.warning("HubSpot unreachable: %s", exc)
        return {"status": "error", "code": None}
