import os
import re

from bs4 import BeautifulSoup


def parse_epub(path: str) -> list[dict]:
    """Parse an EPUB file into a list of chapters."""
    import ebooklib
    from ebooklib import epub

    book = epub.read_epub(path, options={"ignore_ncx": True})
    chapters = []
    order = 0

    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        content = item.get_content().decode("utf-8", errors="replace")
        soup = BeautifulSoup(content, "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        text = re.sub(r"\n{3,}", "\n\n", text).strip()

        if len(text) < 20:
            continue

        title = None
        heading = soup.find(["h1", "h2", "h3"])
        if heading:
            title = heading.get_text(strip=True)
        if not title:
            title = f"Chapter {order + 1}"

        chapters.append({"title": title, "content": text, "order": order})
        order += 1

    return chapters


def parse_text(path: str) -> list[dict]:
    """Parse a plain text file into chapters."""
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        text = f.read()

    # Try splitting by "Chapter" headings
    parts = re.split(r"(?i)(?=^chapter\s+\d+)", text, flags=re.MULTILINE)
    parts = [p.strip() for p in parts if p.strip()]

    if len(parts) <= 1:
        # Fall back to splitting by ~2000 char blocks
        parts = _split_by_size(text, 2000)

    chapters = []
    for i, part in enumerate(parts):
        lines = part.split("\n", 1)
        title = lines[0][:80] if lines else f"Section {i + 1}"
        chapters.append({"title": title, "content": part, "order": i})

    return chapters


def parse_file(path: str) -> list[dict]:
    """Dispatch to the right parser based on extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext == ".epub":
        return parse_epub(path)
    elif ext in (".txt", ".text"):
        return parse_text(path)
    else:
        raise ValueError(f"Unsupported file type: {ext}")


def _split_by_size(text: str, max_chars: int = 2000) -> list[str]:
    """Split text into chunks of roughly max_chars, breaking at sentence boundaries."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) > max_chars and current:
            chunks.append(current.strip())
            current = ""
        current += s + " "
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]
