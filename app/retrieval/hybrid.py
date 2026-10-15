from collections import Counter

from langchain_core.documents import Document

RRF_K = 60
MAX_PER_PAGE = 2


def rrf_merge(ranked_lists: list[list[Document]], top_n: int = 5,
              max_per_page: int = MAX_PER_PAGE) -> list[Document]:
    scores: dict[str, float] = {}
    docs: dict[str, Document] = {}
    for results in ranked_lists:
        for rank, doc in enumerate(results):
            cid = doc.metadata["id"]
            scores[cid] = scores.get(cid, 0.0) + 1.0 / (RRF_K + rank + 1)
            docs.setdefault(cid, doc)

    picked: list[Document] = []
    per_page: Counter = Counter()
    for cid in sorted(scores, key=scores.get, reverse=True):
        doc = docs[cid]
        title = doc.metadata["title"]
        if per_page[title] >= max_per_page:
            continue
        picked.append(doc)
        per_page[title] += 1
        if len(picked) == top_n:
            break
    return picked


def search(query: str, vectorstore, keyword_index, mode: str = "hybrid",
           top_n: int = 5, pool: int = 20) -> list[Document]:
    """mode: 'vector', 'keyword', or 'hybrid'. Used by the evaluation to compare them."""
    if mode == "vector":
        return vectorstore.similarity_search(query, k=top_n)
    if mode == "keyword":
        return keyword_index.search(query, k=top_n)
    vec = vectorstore.similarity_search(query, k=pool)
    kw = keyword_index.search(query, k=pool)
    return rrf_merge([vec, kw], top_n=top_n)
