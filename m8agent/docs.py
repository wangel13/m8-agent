from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
import re
from urllib import parse
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
DEFAULT_COMPANION_URL = "https://cs.uwaterloo.ca/~plragde/flaneries/TM8C/"


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


def ingest_companion(
    *,
    db_path: Path,
    raw_docs_dir: Path,
    companion_url: str,
) -> IngestStats:
    raw_docs_dir.mkdir(parents=True, exist_ok=True)
    companion_dir = raw_docs_dir / "the_m8_companion"
    companion_dir.mkdir(parents=True, exist_ok=True)

    index_path = companion_dir / "index.html"
    download_file(companion_url, index_path)
    chapter_urls = extract_companion_chapter_urls(
        index_path.read_text(encoding="utf-8", errors="replace"),
        companion_url,
    )

    pages: list[tuple[Path, str]] = []
    for url in chapter_urls:
        filename = Path(parse.urlparse(url).path).name or "index.html"
        path = companion_dir / filename
        download_file(url, path)
        pages.append((path, url))

    chunks: list[tuple[str, str, str]] = []
    for path, url in pages:
        chunks.extend(parse_companion_html(path, url))

    conn = connect(db_path)
    init_db(conn)
    companion_doc = Document(
        document_id="the_m8_companion",
        title="The M8 Companion",
        source_type="companion",
        authority="community",
        url=companion_url,
        version=None,
    )
    upsert_document(conn, companion_doc)
    replace_doc_chunks(
        conn,
        document_id=companion_doc.document_id,
        source_type=companion_doc.source_type,
        authority=companion_doc.authority,
        source_file=companion_dir,
        chunks=chunks,
    )
    conn.commit()
    conn.close()

    return IngestStats(documents=1, chunks=len(chunks))


def download_file(url: str, path: Path) -> None:
    req = request.Request(url, headers={"User-Agent": "m8agent/0.1"})
    with request.urlopen(req, timeout=90) as response:
        path.write_bytes(response.read())


def extract_companion_chapter_urls(html: str, source_url: str) -> list[str]:
    parser = CompanionLinkParser(source_url)
    parser.feed(html)
    return parser.urls


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


def parse_companion_html(path: Path, source_url: str) -> list[tuple[str, str, str]]:
    parser = CompanionContentParser(source_url)
    parser.feed(path.read_text(encoding="utf-8", errors="replace"))
    return parser.chunks()


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


class CompanionLinkParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self.urls: list[str] = []
        self._seen: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        href = dict(attrs).get("href")
        if not href or href.startswith(("#", "javascript:")):
            return
        url = parse.urljoin(self.base_url, href.split("#", 1)[0])
        parsed = parse.urlparse(url)
        if not parsed.path.endswith(".html"):
            return
        if not url.startswith(self.base_url) or url in self._seen:
            return
        self._seen.add(url)
        self.urls.append(url)


class CompanionContentParser(HTMLParser):
    BLOCK_TAGS = {"p", "li", "pre"}
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta"}

    def __init__(self, source_url: str):
        super().__init__(convert_charrefs=True)
        self.source_url = source_url
        self.in_main = False
        self.main_depth = 0
        self.skip_depth = 0
        self.current_heading = "Introduction"
        self.current_anchor: str | None = None
        self.pending_anchor: str | None = None
        self.active_block: str | None = None
        self.block_parts: list[str] = []
        self.raw_chunks: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = dict(attrs)
        class_tokens = set((attr_map.get("class") or "").split())

        if self.in_main and tag not in self.VOID_TAGS:
            self.main_depth += 1

        if tag == "div" and "main" in class_tokens and not self.in_main:
            self.in_main = True
            self.main_depth = 1
            return

        if not self.in_main:
            return

        if tag in {"script", "style"}:
            self.skip_depth += 1
            return

        if tag == "a" and attr_map.get("name"):
            self.pending_anchor = attr_map["name"]

        if re.fullmatch(r"h[1-6]", tag):
            self._start_block("heading")
        elif tag in self.BLOCK_TAGS:
            self._start_block(tag)
        elif tag == "br" and self.active_block:
            self.block_parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if not self.in_main:
            return

        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1

        if self.active_block == "heading" and re.fullmatch(r"h[1-6]", tag):
            heading = (
                clean_document_text(" ".join(self.block_parts))
                .replace("\U0001f517", "")
                .strip()
            )
            self.block_parts = []
            self.active_block = None
            if heading:
                self.current_heading = heading
                self.current_anchor = self.pending_anchor
            self.pending_anchor = None
        elif self.active_block == tag and tag in self.BLOCK_TAGS:
            self._flush_text_block()

        if tag not in self.VOID_TAGS:
            self.main_depth -= 1
            if self.main_depth <= 0:
                self.in_main = False

    def handle_data(self, data: str) -> None:
        if not self.in_main or self.skip_depth or not self.active_block:
            return
        value = data.strip()
        if value:
            self.block_parts.append(value)

    def chunks(self) -> list[tuple[str, str, str]]:
        chunks: list[tuple[str, str, str]] = []
        for location, citation_url, text in self.raw_chunks:
            for part in chunk_text(text):
                chunks.append((location, citation_url, part))
        return chunks

    def _start_block(self, tag: str) -> None:
        if self.active_block and self.active_block != "heading":
            self._flush_text_block()
        self.active_block = tag
        self.block_parts = []

    def _flush_text_block(self) -> None:
        text = clean_document_text(" ".join(self.block_parts))
        self.block_parts = []
        self.active_block = None
        if not text:
            return
        self.raw_chunks.append((self.current_heading, self._citation_url(), text))

    def _citation_url(self) -> str:
        if not self.current_anchor:
            return self.source_url
        return f"{self.source_url}#{parse.quote(self.current_anchor, safe='')}"
