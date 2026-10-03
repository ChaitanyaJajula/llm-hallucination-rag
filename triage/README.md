# Triage — an AI support inbox

Tickets come in, an LLM tags them and drafts a reply, an agent edits, approves, and "sends".
Built for the YC founding-engineer take-home practice (brief: 4-person startup, show a design partner Monday).

## Run it
```bash
cd triage
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...      # optional; without it the rule-based fallback is used
uvicorn app.main:app --reload            # http://localhost:8000 → "Load 6 sample tickets"
pytest                                   # 10 tests, no network needed
python -m eval.run_eval                  # accuracy on 10 hand-labeled tickets
```
Deploy: `Dockerfile` + `render.yaml` (Render, 1 GB disk for SQLite). Set `ANTHROPIC_API_KEY` in the dashboard — keys are never committed. **No auth** (out of scope per the brief): anyone with the URL sees the inbox.

## Architecture
- **FastAPI + Jinja (server-rendered) + SQLite.** One process, no build step, deploys anywhere. A SPA would add a second codebase for a 3-screen tool.
- `app/llm.py` — one LLM call per ticket returns triage *and* draft as JSON (one call = half the cost/latency of two). Output is parsed and validated with pydantic (enum categories, urgency 1–3).
- Failure handling: the ticket is **saved before** any AI runs. Timeout / 429 / 5xx / malformed JSON → one retry (malformed output is re-prompted with the error) → deterministic keyword fallback, labelled `fallback` in the UI with a "Retry AI" button. `triage()` never raises.
- `app/prompts.py` — all prompt text in one file. Ticket text is wrapped and declared untrusted (prompt-injection hygiene).
- Inbox sort: escalated first (Enterprise + urgency 1, not yet sent), then urgency, then oldest-waiting. Filters by category/status.
- Stretch done: escalation rule, 10-ticket eval, cost + latency per ticket (`app/config.py` price table).

## Trade-offs
- Sync LLM call inside the request (~1–3 s). Fine for 6 tickets; see below for scale.
- "Send" only flips status — no email is actually sent.
- Fallback rules are tuned on the sample tickets, so its **100% category accuracy on the eval is overfit and means little**. The number that matters is the LLM run, which I have **not** been able to run (no API key in the build environment) — run `python -m eval.run_eval` with a key before trusting the prompt.

## With another week
Background queue + worker for triage (50k/day breaks the sync call and SQLite writes → Postgres + queue); Anthropic prompt caching on the system prompt and a cheaper model for easy tickets (cost lever); knowledge-base grounding for drafts; real email in/out; auth; a bigger eval set that also scores draft quality.

## Status vs. the brief — honest checklist
Done: ingest (CSV + form + `POST /tickets` JSON), structured triage, plan-aware draft, inbox with filters/sort, detail/edit/approve, SQLite persistence, LLM-failure handling, tests, eval.
**Not done (needs you):** public deployment (no hosting access from here), 2–3 min video, and the walkthrough.

## AI usage
Written with Claude Code in one session: it scaffolded everything here; I'd expect you to read it and be able to rewrite `llm.py` from scratch before the walkthrough — that's the rule of thumb in the brief.
