import csv
from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, Field

from . import config, db, llm

@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init()
    yield


app = FastAPI(title="Triage", lifespan=lifespan)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

CATEGORIES = ["billing", "bug", "how-to", "cancellation", "feature request", "other"]
STATUSES = ["new", "approved", "sent"]


class TicketIn(BaseModel):
    customer_email: str = Field(min_length=3, max_length=254, pattern=r"^[^@\s]+@[^@\s]+$")
    plan: str = "Free"
    subject: str = Field(min_length=1, max_length=300)
    body: str = Field(min_length=1, max_length=10_000)
    received_at: str | None = None


def is_escalated(row) -> bool:
    return row["plan"] == "Enterprise" and row["urgency"] == 1 and row["status"] != "sent"


def _insert(conn, t: TicketIn) -> int:
    cur = conn.execute(
        "INSERT INTO tickets (customer_email, plan, subject, body, received_at) VALUES (?,?,?,?,?)",
        (t.customer_email, t.plan, t.subject, t.body,
         t.received_at or datetime.now(timezone.utc).isoformat(timespec="seconds")),
    )
    return cur.lastrowid


def run_triage(ticket_id: int) -> None:
    """Triage one stored ticket. The ticket row exists first, so no failure can lose it."""
    with db.session() as c:
        row = c.execute("SELECT plan, subject, body FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if not row:
        return
    r = llm.triage(row["plan"], row["subject"], row["body"])
    with db.session() as c:
        c.execute(
            """UPDATE tickets SET category=?, urgency=?, sentiment=?, summary=?, draft=?,
               ai_source=?, ai_error=?, cost_usd=?, latency_ms=? WHERE id=? AND status='new'""",
            (r.category, r.urgency, r.sentiment, r.summary, r.draft_reply,
             r.source, r.error, r.cost_usd, r.latency_ms, ticket_id),
        )


def _get(ticket_id: int):
    with db.session() as c:
        row = c.execute("SELECT * FROM tickets WHERE id=?", (ticket_id,)).fetchone()
    if not row:
        raise HTTPException(404, "ticket not found")
    return row


@app.get("/healthz")
def healthz():
    return {"ok": True, "llm": "configured" if config.API_KEY else "fallback-only"}


@app.get("/", response_class=HTMLResponse)
def inbox(request: Request, category: str = "", status: str = ""):
    where, args = [], []
    if category in CATEGORIES:
        where.append("category=?"); args.append(category)
    if status in STATUSES:
        where.append("status=?"); args.append(status)
    sql = "SELECT * FROM tickets" + (" WHERE " + " AND ".join(where) if where else "")
    with db.session() as c:
        rows = c.execute(sql, args).fetchall()
        total = c.execute("SELECT COUNT(*) FROM tickets").fetchone()[0]
        counts = c.execute(
            "SELECT category, COUNT(*) n FROM tickets WHERE substr(received_at,1,10)=? GROUP BY category",
            (datetime.now(timezone.utc).date().isoformat(),),
        ).fetchall()
    # Escalated first, then most urgent (1), un-triaged last, then oldest first (waiting longest).
    rows = sorted(rows, key=lambda r: (not is_escalated(r), r["urgency"] or 9, r["received_at"]))
    return templates.TemplateResponse(request, "inbox.html", {
        "tickets": rows, "total": total, "category": category, "status": status,
        "categories": CATEGORIES, "statuses": STATUSES, "is_escalated": is_escalated,
        "today_counts": counts, "llm_on": bool(config.API_KEY),
    })


@app.post("/tickets")
async def create_ticket(request: Request):
    """Accepts JSON (API) or an HTML form."""
    is_json = "application/json" in request.headers.get("content-type", "")
    try:
        if is_json:
            data = await request.json()
        else:
            data = dict((await request.form()).items())
        t = TicketIn(**data)
    except Exception as e:
        if is_json:
            return JSONResponse({"error": "invalid ticket", "detail": str(e)[:500]}, status_code=422)
        return RedirectResponse("/?error=invalid", status_code=303)
    with db.session() as c:
        tid = _insert(c, t)
    run_triage(tid)
    if is_json:
        return JSONResponse(dict(_get(tid)), status_code=201)
    return RedirectResponse(f"/tickets/{tid}", status_code=303)


@app.post("/import-sample")
def import_sample():
    with open(config.SAMPLE_CSV, newline="", encoding="utf-8") as f:
        items = [TicketIn(**{k: v for k, v in r.items() if k != "id"}) for r in csv.DictReader(f)]
    with db.session() as c:
        have = {(r["customer_email"], r["subject"]) for r in c.execute("SELECT * FROM tickets")}
        ids = [_insert(c, t) for t in items if (t.customer_email, t.subject) not in have]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(run_triage, ids))
    return RedirectResponse("/", status_code=303)


@app.get("/tickets/{ticket_id}", response_class=HTMLResponse)
def detail(request: Request, ticket_id: int):
    row = _get(ticket_id)
    return templates.TemplateResponse(request, "detail.html", {
        "t": row, "escalated": is_escalated(row),
    })


@app.post("/tickets/{ticket_id}/draft")
def save_draft(ticket_id: int, draft: str = Form(...)):
    row = _get(ticket_id)
    if row["status"] != "new":
        raise HTTPException(409, "draft is locked once approved")
    with db.session() as c:
        c.execute("UPDATE tickets SET draft=? WHERE id=?", (draft, ticket_id))
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.post("/tickets/{ticket_id}/approve")
def approve(ticket_id: int, draft: str = Form("")):
    row = _get(ticket_id)
    if row["status"] != "new":
        return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)
    final = draft.strip() or row["draft"]
    if not final:
        raise HTTPException(422, "cannot approve an empty draft")
    with db.session() as c:
        c.execute("UPDATE tickets SET status='approved', draft=? WHERE id=?", (final, ticket_id))
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.post("/tickets/{ticket_id}/send")
def send(ticket_id: int):
    """Demo 'send': no real email goes out; it just records the final state."""
    row = _get(ticket_id)
    if row["status"] == "approved":
        with db.session() as c:
            c.execute("UPDATE tickets SET status='sent' WHERE id=?", (ticket_id,))
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.post("/tickets/{ticket_id}/retriage")
def retriage(ticket_id: int):
    row = _get(ticket_id)
    if row["status"] == "new":
        run_triage(ticket_id)
    return RedirectResponse(f"/tickets/{ticket_id}", status_code=303)


@app.get("/api/tickets")
def api_list():
    with db.session() as c:
        return [dict(r) for r in c.execute("SELECT * FROM tickets ORDER BY id")]
