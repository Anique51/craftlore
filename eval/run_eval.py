import json
import sys
import time
from pathlib import Path

from groq import RateLimitError

from app.graph import nodes
from app.graph.build import build_graph
from app.retrieval.bm25 import load_keyword_index
from app.retrieval.hybrid import search
from app.retrieval.store import get_vectorstore

QUESTIONS = Path("eval/questions.jsonl")
PROGRESS = Path("eval/progress.jsonl")
RESULTS = Path("eval/results.md")
MODES = ["vector", "keyword", "hybrid"]
TOP_N = 5
PAUSE_BETWEEN_QUESTIONS = 20   # seconds; keeps us under the 8,000 tokens/minute limit


def load_verified() -> list[dict]:
    rows = [json.loads(l) for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [q for q in rows if q["verified"]]


def load_progress() -> dict[int, dict]:
    if not PROGRESS.exists():
        return {}
    rows = [json.loads(l) for l in PROGRESS.read_text(encoding="utf-8").splitlines() if l.strip()]
    return {r["id"]: r for r in rows}


def save_progress(record: dict) -> None:
    with PROGRESS.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def with_retry(fn, *args, **kwargs):
    """Call fn; on a rate-limit error, wait and try again."""
    for attempt in range(6):
        try:
            return fn(*args, **kwargs)
        except RateLimitError:
            wait = 30 * (attempt + 1)
            print(f"  rate limited, waiting {wait}s")
            time.sleep(wait)
    raise RuntimeError("Still rate limited after 6 retries. Rerun later; progress is saved.")


def main() -> None:
    full = "--full" in sys.argv
    qs = load_verified()
    wiki_qs = [q for q in qs if q["group"] in ("lore", "version", "hard")]
    done = load_progress()
    print(f"Verified questions: {len(qs)} (wiki: {len(wiki_qs)}), already saved: {len(done)}")

    vectorstore = get_vectorstore()
    keyword_index = load_keyword_index()

    # Retrieval is local and free, so it always runs in full.
    recall = {m: 0 for m in MODES}
    for q in wiki_qs:
        for mode in MODES:
            docs = search(q["question"], vectorstore, keyword_index, mode=mode, top_n=TOP_N)
            if any(d.metadata["title"] in q["expected_sources"] for d in docs):
                recall[mode] += 1
    print("Retrieval done")

    graph = build_graph() if full else None
    for q in qs:
        record = done.get(q["id"], {"id": q["id"]})
        if "route_ok" not in record:
            route = with_retry(nodes.router, {"question": q["question"]})["route"]
            record["route_ok"] = route == q["expected_route"]
            time.sleep(3)
        if full and "answer_ok" not in record:
            result = with_retry(graph.invoke, {"question": q["question"], "attempts": 0})
            text = result["answer"].lower()
            record["answer_ok"] = all(k.lower() in text for k in q["answer_keywords"])
            time.sleep(PAUSE_BETWEEN_QUESTIONS)
        if record != done.get(q["id"]):
            save_progress(record)
            done[q["id"]] = record
        print(f"Q{q['id']:>2} route_ok={record.get('route_ok')} answer_ok={record.get('answer_ok')}")

    route_ok = sum(done[q["id"]]["route_ok"] for q in qs)
    answer_ok = sum(done[q["id"]].get("answer_ok", False) for q in qs) if full else None

    n = max(len(wiki_qs), 1)
    lines = [
        "# Evaluation results",
        "",
        f"Verified questions: {len(qs)} (wiki: {len(wiki_qs)}, recipe: {len(qs) - len(wiki_qs)})",
        "",
        "## Retrieval recall@5 (wiki questions)",
        "",
        "| Mode | Recall@5 |",
        "|---|---|",
    ]
    for mode in MODES:
        lines.append(f"| {mode} | {recall[mode]}/{len(wiki_qs)} ({100 * recall[mode] / n:.0f}%) |")
    lines += ["", f"## Routing accuracy: {route_ok}/{len(qs)}"]
    if answer_ok is not None:
        lines += ["", f"## Answer keyword match (full graph): {answer_ok}/{len(qs)}"]

    report = "\n".join(lines) + "\n"
    RESULTS.write_text(report, encoding="utf-8")
    print()
    print(report)


if __name__ == "__main__":
    main()
