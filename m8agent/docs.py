from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from urllib import request

from pypdf import PdfReader

from .db import Document, connect, init_db, replace_doc_chunks, upsert_document
from .vtt import clean_text


DEFAULT_MANUAL_URL = (
    "https://cdn.shopify.com/s/files/1/0455/0485/6229/files/"
    "m8_operation_manual_v20260421.pdf?v=1776791699"
)
DEFAULT_TIPS_URL = (
    "https://docs.google.com/document/d/"
    "1IpUeR2s9TpkwH9w2lfqfLLkUxLvXcQWipDR046DzOYk/export?format=txt"
)


@dataclass(frozen=True)
class IngestStats:
    documents: int
    chunks: int


def ingest_docs(
    *,
    db_path: Path,
    raw_docs_dir: Path,
    manual_url: str,
    tips_url: str,
) -> IngestStats:
    raw_docs_dir.mkdir(parents=True, exist_ok=True)
    manual_path = raw_docs_dir / "m8_operation_manual_v20260421.pdf"
    tips_path = raw_docs_dir / "open_m8_tips_tricks_and_findings.txt"

    download_file(manual_url, manual_path)
    download_file(tips_url, tips_path)

    conn = connect(db_path)
    init_db(conn)

    manual_doc = Document(
        document_id="m8_operation_manual_v20260421",
        title="M8 Operation Manual v6.5.2",
        source_type="manual",
        authority="official",
        url=manual_url,
        version="6.5.2 2026-04-21",
    )
    upsert_document(conn, manual_doc)
    manual_chunks = parse_manual_pdf(manual_path, manual_url)
    replace_doc_chunks(
        conn,
        document_id=manual_doc.document_id,
        source_type=manual_doc.source_type,
        authority=manual_doc.authority,
        source_file=manual_path,
        chunks=manual_chunks,
    )

    tips_doc = Document(
        document_id="open_m8_tips_tricks_and_findings",
        title="Open M8 Tips Tricks and Findings",
        source_type="community_tips",
        authority="community",
        url=tips_url,
        version=None,
    )
    upsert_document(conn, tips_doc)
    tips_chunks = parse_tips_text(tips_path, tips_url)
    replace_doc_chunks(
        conn,
        document_id=tips_doc.document_id,
        source_type=tips_doc.source_type,
        authority=tips_doc.authority,
        source_file=tips_path,
        chunks=tips_chunks,
    )

    conn.commit()
    conn.close()
    return IngestStats(documents=2, chunks=len(manual_chunks) + len(tips_chunks))


def download_file(url: str, path: Path) -> None:
    req = request.Request(url, headers={"User-Agent": "m8agent/0.1"})
    with request.urlopen(req, timeout=90) as response:
        path.write_bytes(response.read())


def parse_manual_pdf(path: Path, source_url: str) -> list[tuple[str, str, str]]:
    reader = PdfReader(str(path))
    chunks: list[tuple[str, str, str]] = []
    for index, page in enumerate(reader.pages, start=1):
        text = clean_document_text(page.extract_text() or "")
        if not text:
            continue
        for part in chunk_text(text):
            location = f"p. {index}"
            citation_url = f"{source_url}#page={index}"
            chunks.append((location, citation_url, part))
    return chunks


def parse_tips_text(path: Path, source_url: str) -> list[tuple[str, str, str]]:
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    chunks: list[tuple[str, str, str]] = []
    heading = "Introduction"
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        text = clean_document_text("\n".join(buffer))
        buffer = []
        if not text:
            return
        for part in chunk_text(text):
            chunks.append((heading, source_url, part))

    for raw_line in lines:
        line = raw_line.strip()
        if not line or set(line) == {"_"}:
            flush()
            continue
        if is_tips_heading(line):
            flush()
            heading = line
            continue
        buffer.append(line)

    flush()
    return chunks


def is_tips_heading(line: str) -> bool:
    if len(line) > 90:
        return False
    if line.startswith(("*", "-", ">", "http", "From ", "from ")):
        return False
    if re.match(r"^\d+\.", line):
        return False
    words = line.split()
    if len(words) <= 6 and not line.endswith((".", ",", ";", ":")):
        return True
    return bool(re.match(r"^[A-Z][A-Za-z0-9 .,&:/()+-]{2,}$", line))


def clean_document_text(text: str) -> str:
    text = text.replace("\ufeff", " ")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    text = re.sub(r"-\s+", "", text)
    text = clean_text(text)
    return text


def chunk_text(text: str, *, max_chars: int = 1_200) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        if len(sentence) > max_chars:
            if current:
                chunks.append(" ".join(current).strip())
                current = []
                current_len = 0
            chunks.extend(split_long_text(sentence, max_chars=max_chars))
            continue

        if current and current_len + len(sentence) + 1 > max_chars:
            chunks.append(" ".join(current).strip())
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += len(sentence) + 1

    if current:
        chunks.append(" ".join(current).strip())
    return [chunk for chunk in chunks if chunk]


def split_long_text(text: str, *, max_chars: int) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current: list[str] = []
    current_len = 0
    for word in words:
        if current and current_len + len(word) + 1 > max_chars:
            chunks.append(" ".join(current))
            current = [word]
            current_len = len(word)
        else:
            current.append(word)
            current_len += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks
