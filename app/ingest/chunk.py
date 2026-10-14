import re
from urllib.parse import quote

import mwparserfromhell
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Matches "== Heading ==" through "====== Heading ======".
HEADING = re.compile(r"^(={2,6})\s*(.+?)\s*\1\s*$", re.MULTILINE)
SPLITTER = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
MIN_BODY_CHARS = 50


def page_url(title: str) -> str:
    return "https://minecraft.wiki/w/" + quote(title.replace(" ", "_"))


def clean(wikitext: str) -> str:
    """Remove templates, links, and markup, keeping the readable text."""
    return str(mwparserfromhell.parse(wikitext).strip_code(normalize=True, collapse=True)).strip()


def split_sections(wikitext: str) -> list[tuple[str, str]]:
    parts = HEADING.split(wikitext)
    sections = [("Intro", parts[0])]
    for i in range(1, len(parts), 3):
        heading = parts[i + 1].strip()
        body = parts[i + 2] if i + 2 < len(parts) else ""
        sections.append((heading, body))
    return sections


def chunk_page(title: str, wikitext: str) -> list[Document]:
    docs: list[Document] = []
    for heading, raw_body in split_sections(wikitext):
        body = clean(raw_body)
        if len(body) < MIN_BODY_CHARS:
            continue

        if heading == "Intro":
            url = page_url(title)
            prefix = f"{title}\n"
        else:
            url = page_url(title) + "#" + quote(heading.replace(" ", "_"))
            prefix = f"{title} - {heading}\n"

        pieces = SPLITTER.split_text(body) if len(body) > 1000 else [body]
        for n, piece in enumerate(pieces):
            docs.append(
                Document(
                    page_content=prefix + piece,
                    metadata={"title": title, "section": heading, "url": url, "chunk_index": n},
                )
            )
    return docs
