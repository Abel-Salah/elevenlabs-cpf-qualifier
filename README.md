# Inbound training qualifier — an ElevenLabs Agents prototype

A French voice agent that answers the phone for a vocational training provider,
works out which public funding routes are worth pursuing, and decides — in the
middle of the call — whether to keep going or hand over to a human.

Built to make one argument concrete: in the French training market, the hard
part of a voice agent is not the voice. It is the domain logic and the handoff.

> **Status: prototype.** The rules engine and the webhook service are covered by
> tests and run offline. Connecting it to a live agent needs an ElevenLabs API
> key and a public URL. Nothing here promises a caller any funding — see
> [Boundaries](#boundaries).

---

## The problem

A training provider gets calls all day. Most of them die on the same question:
*"can this be funded?"* The answer depends on the caller's employment status
and on whether the course is registered with France Compétences — and the
receptionist has to ask four questions in the right order to find out.

Getting it wrong is expensive in both directions. Tell someone they are covered
when they are not and you lose them at enrolment. Send every call to a human and
the qualification cost eats the margin on the course.

## What this does

```
Caller ──► ElevenLabs agent ──► POST /qualify ──► rules engine
                   ▲                                   │
                   │                                   ├─► ask_for:<field>
                   └───────── next_action ◄────────────┼─► transfer_to_human
                                                       └─► confirm_and_book
                                                              │
                                                       HubSpot contact
```

The agent calls `/qualify` every time it learns something new. The service
returns one instruction, never a paragraph — `ask_for:phone`,
`transfer_to_human`, or `confirm_and_book`. A voice agent that has to interpret
a nuanced answer mid-call will improvise; one that receives a single verb will
not.

### Routing rules

| Caller status | Primary route | CPF as fallback |
|---|---|---|
| Private-sector employee | employer's OPCO | only if the course is RNCP/RS registered |
| Public-sector employee | CPF | — (no OPCO route exists) |
| Jobseeker | France Travail | if registered |
| Self-employed | their own FAF (FIFPL, AGEFICE…) | if registered |
| Apprentice | OPCO, via the CFA | — |

Two rules exist because of how these calls actually go wrong:

- **A non-registered course kills the CPF route.** CPF only covers courses
  registered with France Compétences. This is the single most common false hope
  on an inbound call, so it is encoded, not left to the model.
- **An employer under 50 staff triggers a human handoff**, even when the routing
  is unambiguous. The OPCO paperwork is where small employers give up, and a
  callback costs less than a lost enrolment.

## Run it

```bash
pip install -r requirements.txt
pytest                                   # 17 tests, no network, no keys
uvicorn qualifier.server:app --app-dir src --reload
```

```bash
curl -s localhost:8000/qualify -H 'Content-Type: application/json' -d '{
  "full_name": "Marie Durand", "phone": "+33600000000",
  "status": "private_employee", "employer_size": 250,
  "certified_training": true, "course": "Anglais professionnel"
}' | python3 -m json.tool
```

```json
{
  "decision": {
    "routes": ["OPCO", "CPF"],
    "missing": [],
    "handoff": false,
    "score": 85
  },
  "crm": { "status": "dry_run" },
  "next_action": "confirm_and_book"
}
```

`crm.status` is `dry_run` until `HUBSPOT_TOKEN` is set: the pipeline is fully
exercisable without credentials.

### Connect a live agent

```bash
cp .env.example .env          # add ELEVENLABS_API_KEY
python scripts/create_agent.py --webhook-url https://your-public-host --dry-run
python scripts/create_agent.py --webhook-url https://your-public-host
```

The French system prompt and the tool schema live in
[`agent/agent_config.json`](agent/agent_config.json).

## Boundaries

What this deliberately does **not** do, because a voice agent that does it is a
liability:

- It never states an amount, a CPF balance, or a processing time.
- It never confirms entitlement. Entitlement depends on the caller's CPF
  balance, their employer's OPCO agreement and France Travail approval — none of
  which are knowable during a 90-second call. The engine routes and flags.
- It hands over on the second misunderstanding rather than improvising.
- The routing table is a simplified model of French funding rules for
  demonstration purposes. It is not legal or regulatory advice.

## Production gaps

Honest list of what stands between this and a deployment:

- `/qualify` is unauthenticated unless `ELEVENLABS_WEBHOOK_SECRET` is set.
- HubSpot writes are fire-and-forget with no retry queue; a CRM outage during a
  call silently loses the lead rather than dropping the call.
- No deduplication: a caller who rings twice creates two contacts.
- The custom HubSpot properties (`funding_route`, `qualification_score`,
  `agent_handoff`) must be created in the portal first.
- No observability beyond stdlib logging.

## Layout

```
src/qualifier/rules.py    routing engine — pure functions, no I/O
src/qualifier/models.py   Enquiry / Decision, tolerant payload parsing
src/qualifier/server.py   FastAPI webhook called by the agent
src/qualifier/crm.py      HubSpot sink, dry-run by default
agent/agent_config.json   French prompt + tool schema
tests/                    17 tests, offline
```

---

Built by [Abel Salah](https://abelsalah.fr) — AI deployment for French and
Spanish SMEs. [LinkedIn](https://www.linkedin.com/in/abel-salah/)
