import re
from dataclasses import dataclass
from hashlib import sha256

HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")


@dataclass(frozen=True)
class ChunkDraft:
    position: int
    heading_path: tuple[str, ...]
    content: str
    content_hash: str


def chunk_markdown(markdown: str, *, max_characters: int = 1200) -> list[ChunkDraft]:
    """Split Markdown deterministically at headings and bounded paragraph groups."""
    headings: list[str] = []
    sections: list[tuple[tuple[str, ...], list[str]]] = [((), [])]
    for line in markdown.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        match = HEADING.match(line)
        if match:
            level = len(match.group(1))
            headings = headings[: level - 1]
            headings.append(match.group(2).strip())
            sections.append((tuple(headings), [line]))
        else:
            sections[-1][1].append(line)

    chunks: list[ChunkDraft] = []
    for path, lines in sections:
        text = "\n".join(lines).strip()
        if not text:
            continue
        paragraphs = re.split(r"\n{2,}", text)
        current = ""
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            if current and len(current) + len(paragraph) + 2 > max_characters:
                chunks.append(_draft(len(chunks), path, current))
                current = paragraph
            else:
                current = f"{current}\n\n{paragraph}" if current else paragraph
        if current:
            chunks.append(_draft(len(chunks), path, current))
    return chunks


def _draft(position: int, heading_path: tuple[str, ...], content: str) -> ChunkDraft:
    return ChunkDraft(position, heading_path, content, sha256(content.encode()).hexdigest())
