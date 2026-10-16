import json
import shutil
from pathlib import Path

from app.config import settings
from app.ingest.chunk import chunk_page
from app.ingest.drops import drop_docs
from app.retrieval.store import COLLECTION, get_embeddings
from langchain_chroma import Chroma

RAW_DIR = Path("data/raw")
CHUNKS_FILE = Path("data/chunks.json")


def main() -> None:
    docs = []
    for path in sorted(RAW_DIR.glob("*.json")):
        page = json.loads(path.read_text(encoding="utf-8"))
        docs.extend(chunk_page(page["title"], page["wikitext"]))
        docs.extend(drop_docs(page["title"], page["wikitext"]))

    ids = [f"chunk-{i}" for i in range(len(docs))]
    for doc, cid in zip(docs, ids):
        doc.metadata["id"] = cid

    CHUNKS_FILE.write_text(
        json.dumps(
            [{"id": d.metadata["id"], "text": d.page_content, "metadata": d.metadata} for d in docs],
            ensure_ascii=False,
            indent=1,
        ),
        encoding="utf-8",
    )

    shutil.rmtree(settings.chroma_dir, ignore_errors=True)
    store = Chroma(
        collection_name=COLLECTION,
        embedding_function=get_embeddings(),
        persist_directory=settings.chroma_dir,
    )
    store.add_documents(docs, ids=ids)

    pages = len({d.metadata["title"] for d in docs})
    print(f"Pages: {pages}")
    print(f"Chunks: {len(docs)}")
    print(f"Saved: {CHUNKS_FILE} and {settings.chroma_dir}")


if __name__ == "__main__":
    main()
