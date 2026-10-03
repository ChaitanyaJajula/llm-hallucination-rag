"""LLM triage with validation, retry, and a deterministic fallback.

Contract: `triage()` NEVER raises. It returns a validated TriageResult, either
from the model (source="llm") or from rules (source="fallback") with the
reason recorded in `error`, so a ticket is never lost or left half-processed.
"""
import json
import re
import time
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, field_validator

from . import config, prompts

Category = Literal["billing", "bug", "how-to", "cancellation", "feature request", "other"]


class TriageResult(BaseModel):
    category: Category
    urgency: int = Field(ge=1, le=3)
    sentiment: Literal["positive", "neutral", "negative"]
    summary: str = Field(min_length=1, max_length=300)
    draft_reply: str = Field(min_length=1)
    source: Literal["llm", "fallback"] = "llm"
    error: str | None = None
    cost_usd: float | None = None
    latency_ms: int | None = None

    @field_validator("summary", "draft_reply")
    @classmethod
    def _strip(cls, v: str) -> str:
        return v.strip()


def _client():
    import anthropic

    return anthropic.Anthropic(api_key=config.API_KEY, timeout=config.LLM_TIMEOUT_S, max_retries=1)


def _call(messages: list[dict]) -> tuple[str, int, int]:
    """One model call. Returns (text, input_tokens, output_tokens). Patched in tests."""
    resp = _client().messages.create(
        model=config.MODEL, max_tokens=700, system=prompts.SYSTEM, messages=messages
    )
    text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
    return text, resp.usage.input_tokens, resp.usage.output_tokens


def parse(text: str) -> TriageResult:
    """Extract and validate the JSON object; raises ValueError/ValidationError."""
    m = re.search(r"\{.*\}", text, re.DOTALL)  # tolerate prose or ```json fences
    if not m:
        raise ValueError("no JSON object found")
    data = json.loads(m.group(0))
    if isinstance(data.get("urgency"), str) and data["urgency"].strip().isdigit():
        data["urgency"] = int(data["urgency"])
    if isinstance(data.get("category"), str):
        data["category"] = data["category"].strip().lower()
    return TriageResult(**data)


def _cost(i: int, o: int) -> float:
    pin, pout = config.PRICES.get(config.MODEL, (0.0, 0.0))
    return (i * pin + o * pout) / 1_000_000


def triage(plan: str, subject: str, body: str) -> TriageResult:
    t0 = time.monotonic()
    if not config.API_KEY:
        return _finish(fallback(plan, subject, body, "no ANTHROPIC_API_KEY set"), t0)

    messages = [{"role": "user", "content": prompts.user_prompt(plan, subject, body)}]
    tin = tout = 0
    last_err = "unknown"
    for attempt in range(config.LLM_ATTEMPTS):
        try:
            text, i, o = _call(messages)
            tin, tout = tin + i, tout + o
        except Exception as e:  # timeout, rate limit, 5xx, network: all handled the same
            last_err = f"{type(e).__name__}: {e}"[:200]
            time.sleep(min(2**attempt, 4) * 0.5)
            continue
        try:
            res = parse(text)
            res.cost_usd = _cost(tin, tout)
            return _finish(res, t0)
        except (ValueError, ValidationError) as e:
            last_err = f"invalid model output: {str(e).splitlines()[0]}"[:200]
            messages += [
                {"role": "assistant", "content": text or "(empty)"},
                {"role": "user", "content": prompts.retry_prompt(last_err)},
            ]
    res = fallback(plan, subject, body, last_err)
    res.cost_usd = _cost(tin, tout) if tin else None
    return _finish(res, t0)


def _finish(res: TriageResult, t0: float) -> TriageResult:
    res.latency_ms = int((time.monotonic() - t0) * 1000)
    return res


_RULES = [
    ("billing", 2, ["charge", "refund", "invoice", "billing", "payment", "card"]),
    ("cancellation", 2, ["cancel", "close my account", "unsubscribe"]),
    ("bug", 1, ["500", "error", "broken", "crash", "blocked", "down", "not working", "fails"]),
    ("feature request", 3, ["would love", "feature", "wish", "please add", "integration"]),
    ("how-to", 3, ["how do", "how to", "guide", "set up", "setup", "?"]),
]


def fallback(plan: str, subject: str, body: str, reason: str) -> TriageResult:
    """Keyword rules. Deliberately dumb and clearly labelled so an agent reviews it."""
    text = f"{subject} {body}".lower()
    category, urgency = "other", 3
    for cat, urg, words in _RULES:
        if any(w in text for w in words):
            category, urgency = cat, urg
            break
    negative = any(w in text for w in ["asap", "blocked", "never", "slow", "twice", "unacceptable"])
    if negative and urgency > 1 and category in ("billing", "bug", "cancellation"):
        urgency = max(1, urgency - 1)
    draft = (
        f"Hi,\n\nThanks for reaching out about \"{subject}\". "
        f"We've received your message as a {plan}-plan customer and a member of the team "
        "is looking into it now. We'll follow up shortly with next steps.\n\n"
        "The Triage Support Team"
    )
    return TriageResult(
        category=category,
        urgency=urgency,
        sentiment="negative" if negative else "neutral",
        summary=subject[:140],
        draft_reply=draft,
        source="fallback",
        error=reason,
    )
