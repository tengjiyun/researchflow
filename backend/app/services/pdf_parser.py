from dataclasses import dataclass
from pathlib import Path
import re

from pypdf import PdfReader

from app.services.pdf_download import DocumentError

MAX_PAGES = 300
MAX_TEXT_CHARACTERS = 2_000_000
CHUNK_CHARACTERS = 2000
HEADINGS = {
    "abstract": "abstract", "introduction": "introduction",
    "background": "introduction", "methods": "methodology",
    "method": "methodology", "methodology": "methodology",
    "materials and methods": "methodology", "experimental methods": "methodology",
    "results": "results", "findings": "results", "discussion": "discussion",
    "results and discussion": "discussion", "limitations": "limitations",
    "limitations and future work": "limitations", "conclusion": "conclusion",
    "conclusions": "conclusion", "references": "references",
    "bibliography": "references",
}


@dataclass
class ParsedDocument:
    pages: list[str]
    sections: list[dict]
    chunks: list[dict]


def heading_type(line: str) -> str | None:
    heading = re.sub(r"^(?:\d+(?:\.\d+)*[.)]?|[IVX]+[.)])\s+", "", line.strip())
    heading = heading.rstrip(":.").lower()
    return HEADINGS.get(heading)


def organise_pages(pages: list[str]) -> ParsedDocument:
    sections = []
    chunks = []
    current = None

    def add_text(page: int, start: int, end: int):
        nonlocal current
        text = pages[page - 1]
        if not text[start:end].strip():
            return
        if current is None:
            current = {
                "section_type": "unknown", "original_heading": None,
                "sequence_number": len(sections) + 1, "start_page": page, "end_page": page,
            }
            sections.append(current)
        current["end_page"] = page
        while start < end:
            stop = min(start + CHUNK_CHARACTERS, end)
            if stop < end:
                boundary = max(text.rfind("\n", start + CHUNK_CHARACTERS // 2, stop),
                               text.rfind(" ", start + CHUNK_CHARACTERS // 2, stop))
                if boundary >= 0:
                    stop = boundary + 1
            chunks.append({
                "section_sequence": current["sequence_number"],
                "sequence_number": len(chunks) + 1, "source_text": text[start:stop],
                "start_page": page, "end_page": page,
                "start_character": start, "end_character": stop,
            })
            start = stop

    for page_number, text in enumerate(pages, start=1):
        start = offset = 0
        for line in text.splitlines(keepends=True):
            category = heading_type(line)
            if category is not None:
                add_text(page_number, start, offset)
                current = {
                    "section_type": category, "original_heading": line.strip(),
                    "sequence_number": len(sections) + 1,
                    "start_page": page_number, "end_page": page_number,
                }
                sections.append(current)
                start = offset
            offset += len(line)
        add_text(page_number, start, len(text))
    return ParsedDocument(pages, sections, chunks)


def parse_pdf(path: Path) -> ParsedDocument:
    try:
        with path.open("rb") as stream:
            reader = PdfReader(stream, strict=False)
            if reader.is_encrypted:
                raise DocumentError("pdf_encrypted", "Password-protected PDFs are not supported.")
            if not 1 <= len(reader.pages) <= MAX_PAGES:
                raise DocumentError("pdf_page_limit", "The PDF must contain between 1 and 300 pages.")
            pages = []
            total = 0
            for page in reader.pages:
                text = (page.extract_text(extraction_mode="layout") or "") if "/Contents" in page else ""
                total += len(text)
                if total > MAX_TEXT_CHARACTERS:
                    raise DocumentError("pdf_text_limit", "The extracted text exceeds the supported size.")
                pages.append(text)
    except DocumentError:
        raise
    except Exception as exc:
        raise DocumentError("pdf_parse_failed", "The PDF could not be parsed.") from exc
    if sum(character.isalnum() for text in pages for character in text) < 100:
        raise DocumentError("pdf_text_unavailable", "The PDF has too little readable text. Scanned PDFs are not supported.")
    return organise_pages(pages)
