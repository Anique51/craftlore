import re

from langchain_core.documents import Document

from app.ingest.chunk import page_url

# Matches {{DropLine|name=Rotten Flesh|quantity=0-2|...}} and captures the item name.
DROP_LINE = re.compile(r"\{\{DropLine\|name=([^|}]+)")


def drop_docs(title: str, wikitext: str) -> list[Document]:
    """One 'Drops' chunk per page, listing every item named in its DropLine templates."""
    names: list[str] = []
    for m in DROP_LINE.finditer(wikitext):
        name = m.group(1).strip()
        if name and name not in names:
            names.append(name)
    if not names:
        return []
    items = ', '.join(names)
    text = (
        f"{title} - Drops\n"
        f"What does a {title.lower()} drop when it dies or is killed? "
        f"A {title.lower()} drops: {items}."
    )
    return [
        Document(
            page_content=text,
            metadata={
                "title": title,
                "section": "Drops",
                "url": page_url(title) + "#Drops",
                "chunk_index": 0,
            },
        )
    ]
