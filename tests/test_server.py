from fastapi.testclient import TestClient

from qualifier.server import app

client = TestClient(app)

COMPLETE = {
    "full_name": "Marie Durand",
    "phone": "+33600000000",
    "status": "private_employee",
    "employer_size": 250,
    "certified_training": True,
    "email": "marie@example.fr",
    "course": "Anglais professionnel",
}


def test_health():
    assert client.get("/health").json() == {"status": "ok"}


def test_complete_enquiry_is_confirmed_and_pushed_in_dry_run():
    body = client.post("/qualify", json=COMPLETE).json()
    assert body["next_action"] == "confirm_and_book"
    assert body["crm"]["status"] == "dry_run"
    assert body["crm"]["properties"]["funding_route"] == "OPCO,CPF"


def test_incomplete_enquiry_asks_for_the_missing_field():
    payload = {k: v for k, v in COMPLETE.items() if k != "phone"}
    body = client.post("/qualify", json=payload).json()
    assert body["next_action"] == "ask_for:phone"
    assert body["crm"]["status"] == "skipped"


def test_small_employer_is_transferred():
    body = client.post("/qualify", json={**COMPLETE, "employer_size": 8}).json()
    assert body["next_action"] == "transfer_to_human"


def test_invalid_json_is_rejected():
    response = client.post("/qualify", content=b"not json", headers={"Content-Type": "application/json"})
    assert response.status_code == 400


def test_signature_is_enforced_when_a_secret_is_set(monkeypatch):
    monkeypatch.setenv("ELEVENLABS_WEBHOOK_SECRET", "s3cret")
    assert client.post("/qualify", json=COMPLETE).status_code == 401
