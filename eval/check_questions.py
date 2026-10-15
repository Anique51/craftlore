import json
from pathlib import Path

from app.tools.recipes import lookup_recipe

QUESTIONS = Path("eval/questions.jsonl")
CHUNKS = Path("data/chunks.json")


def main() -> None:
    chunks = json.loads(CHUNKS.read_text(encoding="utf-8"))
    indexed_titles = {c["metadata"]["title"] for c in chunks}
    text_by_title: dict[str, str] = {}
    for c in chunks:
        title = c["metadata"]["title"]
        text_by_title[title] = text_by_title.get(title, "") + " " + c["text"].lower()

    problems = 0
    rows = [json.loads(l) for l in QUESTIONS.read_text(encoding="utf-8").splitlines() if l.strip()]
    for q in rows:
        if q["group"] == "mechanics":
            haystack = lookup_recipe.invoke({"item_name": q["item"]}).lower()
            where = "recipe tool"
        else:
            missing_pages = [s for s in q["expected_sources"] if s not in indexed_titles]
            if missing_pages:
                print(f"Q{q['id']:>2} FAIL       page not indexed: {missing_pages}  {q['question']}")
                problems += 1
                continue
            haystack = " ".join(text_by_title[s] for s in q["expected_sources"])
            where = "index"

        missing = [k for k in q["answer_keywords"] if k.lower() not in haystack]
        if not q["verified"]:
            status = "UNVERIFIED"
        elif missing:
            status = "MISSING"
            problems += 1
        else:
            status = "OK"

        print(f"Q{q['id']:>2} {status:<10} {where:<11} {q['question']}")
        if missing:
            print(f"        keywords not found: {missing}")

    print(f"\nProblems: {problems}")


if __name__ == "__main__":
    main()
