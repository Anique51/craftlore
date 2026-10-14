import json
import re
from pathlib import Path

from langchain_core.documents import Document
from rank_bm25 import BM25Okapi

CHUNKS_FILE = Path("data/chunks.json")
TOKEN_PATTERN = re.compile(r"[a-z0-9_:']+")

# Common words that carry no meaning for matching. Removing them stops
# chunks from scoring points just because they contain "the" or "from".
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "come", "did", "do",
    "does", "for", "from", "get", "how", "i", "in", "is", "it", "my", "of",
    "on", "or", "the", "this", "that", "to", "was", "were", "what", "where",
    "when", "which", "who", "why", "with", "you", "your",
}


def tokenize(text: str) -> list[str]:
    """Lowercase, split into word tokens, and drop stopwords."""
    return [t for t in TOKEN_PATTERN.findall(text.lower()) if t not in STOPWORDS]


class KeywordIndex:
    def __init__(self, docs: list[Document]):
        self.docs = docs
        self.bm25 = BM25Okapi([tokenize(d.page_content) for d in docs])

    def search(self, query: str, k: int = 10) -> list[Document]:
        tokens = tokenize(query)
        if not tokens:
            return []
        scores = self.bm25.get_scores(tokens)
        ranked = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        return [self.docs[i] for i in ranked if scores[i] > 0]


def load_keyword_index(path: Path = CHUNKS_FILE) -> KeywordIndex:
    rows = json.loads(path.read_text(encoding="utf-8"))
    docs = [Document(page_content=r["text"], metadata=r["metadata"]) for r in rows]
    return KeywordIndex(docs)
