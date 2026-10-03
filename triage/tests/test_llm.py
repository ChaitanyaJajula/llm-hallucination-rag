import json

import pytest

from app import llm

GOOD = {"category": "billing", "urgency": 1, "sentiment": "negative",
        "summary": "Double charge", "draft_reply": "Hi, we are checking."}


@pytest.fixture(autouse=True)
def _key(monkeypatch):
    monkeypatch.setattr(llm.config, "API_KEY", "k")
    monkeypatch.setattr(llm.time, "sleep", lambda s: None)


def fake(responses):
    it = iter(responses)

    def _call(messages):
        r = next(it)
        if isinstance(r, Exception):
            raise r
        return r, 100, 50
    return _call


def test_valid_json_in_code_fence(monkeypatch):
    monkeypatch.setattr(llm, "_call", fake(["```json\n" + json.dumps(GOOD) + "\n```"]))
    r = llm.triage("Pro", "s", "b")
    assert r.source == "llm" and r.category == "billing" and r.cost_usd > 0


def test_malformed_then_valid_retries(monkeypatch):
    monkeypatch.setattr(llm, "_call", fake(["not json at all", json.dumps(GOOD)]))
    assert llm.triage("Pro", "s", "b").source == "llm"


def test_out_of_range_urgency_falls_back(monkeypatch):
    bad = json.dumps({**GOOD, "urgency": 9})
    monkeypatch.setattr(llm, "_call", fake([bad, bad]))
    r = llm.triage("Pro", "Charged twice", "refund please")
    assert r.source == "fallback" and 1 <= r.urgency <= 3 and r.category == "billing"


def test_timeouts_never_raise(monkeypatch):
    monkeypatch.setattr(llm, "_call", fake([TimeoutError("slow"), TimeoutError("slow")]))
    r = llm.triage("Free", "API returns 500", "we're blocked")
    assert r.source == "fallback" and "TimeoutError" in r.error and r.category == "bug"


def test_no_key_uses_fallback(monkeypatch):
    monkeypatch.setattr(llm.config, "API_KEY", "")
    assert llm.triage("Pro", "Feature idea", "would love dark mode").category == "feature request"
