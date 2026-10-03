"""Tiny eval: runs the triage pipeline on 10 hand-labeled tickets and prints accuracy.

    python -m eval.run_eval          # uses the LLM if ANTHROPIC_API_KEY is set, else the fallback
Urgency is scored exact and within-one (it's a judgement call; off-by-one is usually fine).
"""
import csv
from pathlib import Path

from app import llm

rows = list(csv.DictReader(open(Path(__file__).with_name("labeled.csv"), encoding="utf-8")))
cat_ok = urg_ok = urg_near = n_fallback = 0
cost = lat = 0.0
for r in rows:
    res = llm.triage(r["plan"], r["subject"], r["body"])
    c, u = res.category == r["category"], res.urgency == int(r["urgency"])
    cat_ok += c; urg_ok += u; urg_near += abs(res.urgency - int(r["urgency"])) <= 1
    n_fallback += res.source == "fallback"; cost += res.cost_usd or 0; lat += res.latency_ms or 0
    print(f"{'ok ' if c else 'BAD'} cat={res.category:<16} (want {r['category']:<16}) urg={res.urgency} (want {r['urgency']}) [{res.source}] {r['subject']}")
n = len(rows)
print(f"\ncategory accuracy {cat_ok}/{n} = {cat_ok/n:.0%} | urgency exact {urg_ok/n:.0%}, within-1 {urg_near/n:.0%}")
print(f"fallback used {n_fallback}/{n} | total cost ${cost:.4f} | avg latency {lat/n:.0f} ms")
