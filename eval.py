"""Evaluate the SQL generator on eval_questions.json.

Metric: execution accuracy = the generated SQL returns the same rows as the gold SQL
(order-insensitive; numbers compared to 2 decimals; column names/order ignored).
Modes:  full = whole schema, no examples   |   rag = retrieved tables + 3 few-shot examples

Usage:  python eval.py            (all questions, both modes)
        python eval.py --limit 5  (quick smoke run)
"""
import argparse
import datetime
import decimal
import json
import statistics
import time
from collections import Counter

import sqlglot
from sqlglot import exp

import db
import llm
import rag

MODES = {"full": False, "rag": True}


def normalize(value) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float, decimal.Decimal)) and not isinstance(value, bool):
        return f"{float(value):.2f}"
    if isinstance(value, (datetime.date, datetime.datetime)):
        return value.isoformat()
    return str(value).strip()


def result_signature(rows: list[dict]) -> Counter:
    """Multiset of rows; each row's values are sorted so column order/names don't matter."""
    return Counter(tuple(sorted(normalize(v) for v in row.values())) for row in rows)


def tables_in(sql: str) -> set[str]:
    return {f"{t.db}.{t.name}".lower() for t in sqlglot.parse_one(sql, read="mysql").find_all(exp.Table)}


def evaluate(limit: int | None = None) -> dict:
    cfg = db.demo_config()
    engine = db.get_engine(cfg)
    print("Index:", rag.ensure_index(engine, cfg))
    eval_key = f"{db.connection_key(cfg)}_eval"
    print("Few-shot examples (clean copy of few_shot.json):", rag.reset_examples(eval_key))

    questions = json.load(open("eval_questions.json", encoding="utf-8"))[:limit]
    details = []
    for q in questions:
        gold = result_signature(db.run_query(engine, q["gold_sql"]))
        gold_tables = tables_in(q["gold_sql"])
        for mode, use_rag in MODES.items():
            start = time.perf_counter()
            try:
                gen = llm.generate_sql(engine, cfg, q["question"], use_rag=use_rag, examples_key=eval_key)
            except Exception as exc:
                gen = {"sql": "", "error": str(exc), "attempts": [], "retrieved": [], "prompt_tokens": 0}
            latency = time.perf_counter() - start

            correct, error = False, gen["error"]
            if not error:
                try:
                    correct = result_signature(db.run_query(engine, gen["sql"])) == gold
                except Exception as exc:
                    error = str(exc).splitlines()[0]
            sent = {t["name"].lower() for t in gen["retrieved"]}
            details.append({
                "id": q["id"], "category": q["category"], "mode": mode, "question": q["question"],
                "gold_sql": q["gold_sql"], "generated_sql": gen["sql"], "correct": correct, "error": error,
                "prompt_tokens": gen["prompt_tokens"], "latency_s": round(latency, 2),
                "attempts": len(gen["attempts"]), "tables_sent": len(sent),
                "gold_tables_found": bool(sent) and gold_tables <= sent,
            })
            print(f"{q['id']:8} {mode:4} {'PASS' if correct else 'FAIL'}  {latency:4.1f}s  "
                  f"{gen['prompt_tokens']:5} tok  {error or ''}"[:140])

    summary = {}
    for mode in MODES:
        rows = [d for d in details if d["mode"] == mode]
        summary[mode] = {
            "accuracy": round(100 * sum(d["correct"] for d in rows) / len(rows), 1),
            "by_category": {c: round(100 * statistics.mean(d["correct"] for d in rows if d["category"] == c), 1)
                            for c in dict.fromkeys(d["category"] for d in rows)},
            "avg_prompt_tokens": round(statistics.mean(d["prompt_tokens"] for d in rows)),
            "avg_latency_s": round(statistics.mean(d["latency_s"] for d in rows), 2),
            "avg_tables_sent": round(statistics.mean(d["tables_sent"] for d in rows), 1),
            "gold_table_recall": round(100 * statistics.mean(d["gold_tables_found"] for d in rows), 1),
            "self_corrected": sum(d["attempts"] > 1 for d in rows),
        }
    return {"run_at": datetime.datetime.now().isoformat(timespec="seconds"), "model": llm.get_model(),
            "questions": len(questions), "summary": summary, "details": details}


def print_table(results: dict) -> None:
    s = results["summary"]
    print(f"\nModel: {results['model']}   Questions: {results['questions']}\n")
    print(f"{'Metric':28} {'Full schema':>12} {'RAG + few-shot':>15}")
    print("-" * 57)
    for label, key, unit in [("Execution accuracy", "accuracy", "%"), ("Avg prompt tokens", "avg_prompt_tokens", ""),
                             ("Avg latency", "avg_latency_s", " s"), ("Avg tables sent", "avg_tables_sent", ""),
                             ("Gold tables in prompt", "gold_table_recall", "%"), ("Self-corrected queries", "self_corrected", "")]:
        print(f"{label:28} {str(s['full'][key]) + unit:>12} {str(s['rag'][key]) + unit:>15}")
    for category in s["full"]["by_category"]:
        print(f"{'  accuracy: ' + category:28} {str(s['full']['by_category'][category]) + '%':>12} "
              f"{str(s['rag']['by_category'][category]) + '%':>15}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, help="only run the first N questions")
    args = parser.parse_args()
    results = evaluate(args.limit)
    print_table(results)
    with open("eval_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print("\nSaved eval_results.json")
