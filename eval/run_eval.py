import json
import sys
import time
from pathlib import Path

from app.graph import nodes
from app.graph.build import build_graph
from app.retrieval.bm25 import load_keyword_index
from app.retrieval.hybrid import search
from app.retrieval.store import get_vectorstore

QUESTIONS = Path("eval/questions.jsonl")
RESULTS = Path("eval/results.md")
MODES = ["vector", "keyword", "hybrid"]
GROQ_PAUSE = 2.5
TOP_N = 5


def load_verified() -> list[dict]:
    rows = [json.loads(l) for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]
    return [q for q in rows if q["verified"]]


def main() -> None:
    full = "--full" in sys.argv
    qs = load_verified()
    wiki_qs = [q for q in qs if q["group"] in ("lore", "version")]
    print(f"Verified questions: {len(qs)} (wiki: {len(wiki_qs)})")

    vectorstore = get_vectorstore()
    keyword_index = load_keyword_index()

    recall = {m: 0 for m in MODES}
    for q in wiki_qs:
        for mode in MODES:
            docs = search(q["question"], vectorstore, keyword_index, mode=mode, top_n=TOP_N)
            if any(d.metadata["title"] in q["expected_sources"] for d in docs):
                recall[mode] += 1
    print("Retrieval done")

    route_ok = 0
    for q in qs:
        route = nodes.router({"question": q["question"]})["route"]
        route_ok += route == q["expected_route"]
        time.sleep(GROQ_PAUSE)
    print("Routing done")

    answer_ok = None
    if full:
        graph = build_graph()
        answer_ok = 0
        for q in qs:
            result = graph.invoke({"question": q["question"], "attempts": 0})
            text = result["answer"].lower()
            answer_ok += all(k.lower() in text for k in q["answer_keywords"])
            time.sleep(10)
        print("Answers done")

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
