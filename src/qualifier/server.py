"""Webhook service exposed to the ElevenLabs agent as a server tool.

The agent calls POST /qualify mid-conversation with whatever it has collected
so far. The response tells the agent what to say next: ask for a missing
field, hand over to a human, or confirm the routing and book.
"""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request

from .crm import push_contact
from .models import Enquiry
from .rules import evaluate

app = FastAPI(title="Inbound training qualifier", version="0.1.0")


def _verify(raw_body: bytes, signature: str | None) -> None:
    """Reject unsigned calls when a shared secret is configured.

    Without ELEVENLABS_WEBHOOK_SECRET the endpoint stays open, which is fine
    on a laptop and wrong in production - hence the README warning.
    """
    secret = os.getenv("ELEVENLABS_WEBHOOK_SECRET")
    if not secret:
        return
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not signature or not hmac.compare_digest(expected, signature):
        raise HTTPException(status_code=401, detail="bad signature")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/qualify")
async def qualify(request: Request, x_signature: str | None = Header(default=None)) -> dict[str, Any]:
    raw = await request.body()
    _verify(raw, x_signature)

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid json")

    enquiry = Enquiry.from_payload(payload if isinstance(payload, dict) else {})
    decision = evaluate(enquiry)

    crm: dict[str, Any] = {"status": "skipped"}
    if decision.complete:
        crm = push_contact(enquiry, decision)

    return {
        "decision": decision.to_dict(),
        "crm": crm,
        "next_action": _next_action(decision),
    }


def _next_action(decision) -> str:
    """The single instruction the agent acts on. One decision, one sentence."""
    if decision.missing:
        return f"ask_for:{decision.missing[0]}"
    if decision.handoff:
        return "transfer_to_human"
    return "confirm_and_book"
