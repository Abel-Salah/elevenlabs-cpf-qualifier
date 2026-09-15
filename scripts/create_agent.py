#!/usr/bin/env python3
"""Create the ElevenLabs agent from agent/agent_config.json.

    python scripts/create_agent.py --webhook-url https://abcd.ngrok.app

Requires ELEVENLABS_API_KEY. Uses the REST endpoint directly (no SDK) so the
request is readable and the failure mode is obvious.

Endpoint: POST https://api.elevenlabs.io/v1/convai/agents/create
Docs:     https://elevenlabs.io/docs/api-reference/agents/create
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
from urllib import error, request

API_URL = "https://api.elevenlabs.io/v1/convai/agents/create"
CONFIG = pathlib.Path(__file__).resolve().parent.parent / "agent" / "agent_config.json"


def build_payload(webhook_url: str) -> dict:
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    for tool in config["conversation_config"]["tools"]:
        if tool["name"] == "qualify":
            tool["api_schema"]["url"] = webhook_url.rstrip("/") + "/qualify"
    return config


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--webhook-url", required=True, help="Public base URL of the qualifier service")
    parser.add_argument("--dry-run", action="store_true", help="Print the payload instead of sending it")
    args = parser.parse_args()

    payload = build_payload(args.webhook_url)

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0

    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        print("ELEVENLABS_API_KEY is not set", file=sys.stderr)
        return 1

    req = request.Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={"xi-api-key": api_key, "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as response:
            body = json.loads(response.read().decode())
    except error.HTTPError as exc:
        print(f"ElevenLabs returned {exc.code}: {exc.read().decode()[:400]}", file=sys.stderr)
        return 1

    print("agent_id:", body.get("agent_id"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
