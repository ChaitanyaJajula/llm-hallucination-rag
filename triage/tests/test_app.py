import json

from app import llm


def _stub(monkeypatch, **over):
    out = {"category": "bug", "urgency": 1, "sentiment": "negative",
           "summary": "s", "draft_reply": "Hello", **over}
    monkeypatch.setattr(llm, "_call", lambda m: (json.dumps(out), 10, 10))


def test_import_sample_and_sort_with_escalation(client, monkeypatch):
    _stub(monkeypatch)
    assert client.post("/import-sample", follow_redirects=False).status_code == 303
    rows = client.get("/api/tickets").json()
    assert len(rows) == 6 and all(r["ai_source"] == "llm" for r in rows)
    html = client.get("/").text
    # Enterprise + urgency 1 tickets are flagged and come before the Pro/Free ones.
    assert html.count("escalate") == 2
    assert html.index("SSO setup?") < html.index("Charged twice")
    client.post("/import-sample")  # idempotent
    assert len(client.get("/api/tickets").json()) == 6


def test_post_tickets_json_and_validation(client, monkeypatch):
    _stub(monkeypatch)
    r = client.post("/tickets", json={"customer_email": "a@b.co", "subject": "Hi", "body": "x"})
    assert r.status_code == 201 and r.json()["status"] == "new"
    assert client.post("/tickets", json={"customer_email": "bad", "subject": "", "body": ""}).status_code == 422


def test_llm_outage_does_not_lose_ticket(client, monkeypatch):
    monkeypatch.setattr(llm, "_call", lambda m: (_ for _ in ()).throw(RuntimeError("429")))
    r = client.post("/tickets", json={"customer_email": "a@b.co", "subject": "Refund", "body": "charged twice"})
    t = r.json()
    assert r.status_code == 201 and t["ai_source"] == "fallback" and t["draft"]


def test_edit_approve_send_flow_and_filters(client, monkeypatch):
    _stub(monkeypatch, category="billing")
    tid = client.post("/tickets", json={"customer_email": "a@b.co", "subject": "Refund", "body": "x"}).json()["id"]
    client.post(f"/tickets/{tid}/approve", data={"draft": "Edited reply"})
    t = client.get("/api/tickets").json()[0]
    assert t["status"] == "approved" and t["draft"] == "Edited reply"
    assert client.post(f"/tickets/{tid}/draft", data={"draft": "late edit"}).status_code == 409
    client.post(f"/tickets/{tid}/send")
    assert client.get("/api/tickets").json()[0]["status"] == "sent"
    assert "Refund" in client.get("/?status=sent&category=billing").text
    assert "No tickets match" in client.get("/?status=new").text


def test_404_and_empty_state(client):
    assert client.get("/tickets/999").status_code == 404
    assert "inbox is empty" in client.get("/").text
