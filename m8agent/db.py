from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import sqlite3

from .vtt import Chunk, format_timestamp


@dataclass(frozen=True)
class Video:
    video_id: str
    title: str
    url: str
    upload_date: str | None
    duration: int | None
    channel: str | None
    description: str | None


@dataclass(frozen=True)
class SearchResult:
    video_id: str
    title: str
    url: str
    lang: str
    start_ms: int
    end_ms: int
    text: str
    score: float

    @property
    def start_seconds(self) -> int:
        return self.start_ms // 1000

    @property
    def timestamp(self) -> str:
        return format_timestamp(self.start_ms)

    @property
    def citation_url(self) -> str:
        return f"{self.url}&t={self.start_seconds}s"


@dataclass(frozen=True)
class Document:
    document_id: str
    title: str
    source_type: str
    authority: str
    url: str
    version: str | None


@dataclass(frozen=True)
class DocChunk:
    document_id: str
    source_type: str
    authority: str
    title: str
    location: str
    citation_url: str
    text: str
    score: float


@dataclass(frozen=True)
class RetrievalResult:
    source_type: str
    authority: str
    title: str
    location: str
    citation_url: str
    text: str
    score: float


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS videos (
            video_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            url TEXT NOT NULL,
            upload_date TEXT,
            duration INTEGER,
            channel TEXT,
            description TEXT
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            video_id TEXT NOT NULL REFERENCES videos(video_id) ON DELETE CASCADE,
            lang TEXT NOT NULL,
            start_ms INTEGER NOT NULL,
            end_ms INTEGER NOT NULL,
            text TEXT NOT NULL,
            source_file TEXT NOT NULL,
            UNIQUE(video_id, lang, start_ms, end_ms)
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
        USING fts5(text, content='chunks', content_rowid='id', tokenize='unicode61');

        CREATE TRIGGER IF NOT EXISTS chunks_ai AFTER INSERT ON chunks BEGIN
            INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
        END;

        CREATE TRIGGER IF NOT EXISTS chunks_ad AFTER DELETE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text)
            VALUES('delete', old.id, old.text);
        END;

        CREATE TRIGGER IF NOT EXISTS chunks_au AFTER UPDATE ON chunks BEGIN
            INSERT INTO chunks_fts(chunks_fts, rowid, text)
            VALUES('delete', old.id, old.text);
            INSERT INTO chunks_fts(rowid, text) VALUES (new.id, new.text);
        END;

        CREATE TABLE IF NOT EXISTS documents (
            document_id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            source_type TEXT NOT NULL,
            authority TEXT NOT NULL,
            url TEXT NOT NULL,
            version TEXT
        );

        CREATE TABLE IF NOT EXISTS doc_chunks (
            id INTEGER PRIMARY KEY,
            document_id TEXT NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
            source_type TEXT NOT NULL,
            authority TEXT NOT NULL,
            location TEXT NOT NULL,
            citation_url TEXT NOT NULL,
            text TEXT NOT NULL,
            source_file TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS doc_chunks_fts
        USING fts5(text, content='doc_chunks', content_rowid='id', tokenize='unicode61');

        CREATE TRIGGER IF NOT EXISTS doc_chunks_ai AFTER INSERT ON doc_chunks BEGIN
            INSERT INTO doc_chunks_fts(rowid, text) VALUES (new.id, new.text);
        END;

        CREATE TRIGGER IF NOT EXISTS doc_chunks_ad AFTER DELETE ON doc_chunks BEGIN
            INSERT INTO doc_chunks_fts(doc_chunks_fts, rowid, text)
            VALUES('delete', old.id, old.text);
        END;

        CREATE TRIGGER IF NOT EXISTS doc_chunks_au AFTER UPDATE ON doc_chunks BEGIN
            INSERT INTO doc_chunks_fts(doc_chunks_fts, rowid, text)
            VALUES('delete', old.id, old.text);
            INSERT INTO doc_chunks_fts(rowid, text) VALUES (new.id, new.text);
        END;
        """
    )
    conn.commit()


def upsert_video(conn: sqlite3.Connection, video: Video) -> None:
    conn.execute(
        """
        INSERT INTO videos(video_id, title, url, upload_date, duration, channel, description)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            title=excluded.title,
            url=excluded.url,
            upload_date=excluded.upload_date,
            duration=excluded.duration,
            channel=excluded.channel,
            description=excluded.description
        """,
        (
            video.video_id,
            video.title,
            video.url,
            video.upload_date,
            video.duration,
            video.channel,
            video.description,
        ),
    )


def get_video_ids(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT video_id FROM videos").fetchall()
    return {row["video_id"] for row in rows}


def replace_chunks(
    conn: sqlite3.Connection,
    *,
    video_id: str,
    lang: str,
    source_file: Path,
    chunks: list[Chunk],
) -> None:
    conn.execute("DELETE FROM chunks WHERE video_id = ? AND lang = ?", (video_id, lang))
    conn.executemany(
        """
        INSERT INTO chunks(video_id, lang, start_ms, end_ms, text, source_file)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        [
            (video_id, lang, chunk.start_ms, chunk.end_ms, chunk.text, str(source_file))
            for chunk in chunks
        ],
    )


def upsert_document(conn: sqlite3.Connection, document: Document) -> None:
    conn.execute(
        """
        INSERT INTO documents(document_id, title, source_type, authority, url, version)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(document_id) DO UPDATE SET
            title=excluded.title,
            source_type=excluded.source_type,
            authority=excluded.authority,
            url=excluded.url,
            version=excluded.version
        """,
        (
            document.document_id,
            document.title,
            document.source_type,
            document.authority,
            document.url,
            document.version,
        ),
    )


def replace_doc_chunks(
    conn: sqlite3.Connection,
    *,
    document_id: str,
    source_type: str,
    authority: str,
    source_file: Path,
    chunks: list[tuple[str, str, str]],
) -> None:
    conn.execute("DELETE FROM doc_chunks WHERE document_id = ?", (document_id,))
    conn.executemany(
        """
        INSERT INTO doc_chunks(
            document_id, source_type, authority, location, citation_url, text, source_file
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        [
            (
                document_id,
                source_type,
                authority,
                location,
                citation_url,
                text,
                str(source_file),
            )
            for location, citation_url, text in chunks
        ],
    )


def video_from_info_json(path: Path) -> Video | None:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("_type") in {"playlist", "channel", "multi_video"}:
        return None

    video_id = data.get("id") or path.parent.name
    if not video_id:
        return None

    webpage_url = data.get("webpage_url") or f"https://www.youtube.com/watch?v={video_id}"
    return Video(
        video_id=video_id,
        title=data.get("title") or video_id,
        url=webpage_url,
        upload_date=data.get("upload_date"),
        duration=data.get("duration"),
        channel=data.get("channel"),
        description=data.get("description"),
    )


def search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 8,
    lang: str | None = None,
) -> list[SearchResult]:
    fts_query = make_fts_query(query)
    params: list[object] = [fts_query]
    lang_clause = ""
    if lang:
        lang_clause = "AND chunks.lang = ?"
        params.append(lang)
    params.append(limit)

    try:
        rows = conn.execute(
            f"""
            SELECT
                videos.video_id,
                videos.title,
                videos.url,
                chunks.lang,
                chunks.start_ms,
                chunks.end_ms,
                chunks.text,
                bm25(chunks_fts) AS score
            FROM chunks_fts
            JOIN chunks ON chunks.id = chunks_fts.rowid
            JOIN videos ON videos.video_id = chunks.video_id
            WHERE chunks_fts MATCH ? {lang_clause}
            ORDER BY score
            LIMIT ?
            """,
            params,
        ).fetchall()
    except sqlite3.OperationalError:
        return fallback_like_search(conn, query, limit=limit, lang=lang)

    return [SearchResult(**dict(row)) for row in rows]


def search_documents(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 8,
    sources: set[str] | None = None,
) -> list[DocChunk]:
    fts_query = make_fts_query(query)
    params: list[object] = [fts_query]
    source_clause = ""
    if sources and "all" not in sources:
        placeholders = ", ".join(["?"] * len(sources))
        source_clause = f"AND doc_chunks.source_type IN ({placeholders})"
        params.extend(sorted(sources))
    params.append(limit)

    try:
        rows = conn.execute(
            f"""
            SELECT
                documents.document_id,
                documents.source_type,
                documents.authority,
                documents.title,
                doc_chunks.location,
                doc_chunks.citation_url,
                doc_chunks.text,
                bm25(doc_chunks_fts) AS score
            FROM doc_chunks_fts
            JOIN doc_chunks ON doc_chunks.id = doc_chunks_fts.rowid
            JOIN documents ON documents.document_id = doc_chunks.document_id
            WHERE doc_chunks_fts MATCH ? {source_clause}
            ORDER BY score
            LIMIT ?
            """,
            params,
        ).fetchall()
    except sqlite3.OperationalError:
        return fallback_doc_like_search(conn, query, limit=limit, sources=sources)

    return [DocChunk(**dict(row)) for row in rows]


def retrieve(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int = 8,
    sources: set[str] | None = None,
    lang: str | None = None,
) -> list[RetrievalResult]:
    normalized_sources = sources or {"all"}
    results: list[RetrievalResult] = []

    if "all" in normalized_sources or "video" in normalized_sources:
        video_limit = limit if normalized_sources == {"video"} else max(limit, 12)
        for item in search(conn, query, limit=video_limit, lang=lang):
            results.append(
                RetrievalResult(
                    source_type="video",
                    authority="community",
                    title=item.title,
                    location=item.timestamp,
                    citation_url=item.citation_url,
                    text=item.text,
                    score=item.score,
                )
            )

    doc_sources = {source for source in normalized_sources if source != "video"}
    if "all" in normalized_sources:
        doc_sources = {"manual", "community_tips", "companion"}
    if doc_sources:
        doc_limit = limit
        if not normalized_sources <= {"manual", "community_tips", "companion"}:
            doc_limit = max(limit, 12)
        for item in search_documents(conn, query, limit=doc_limit, sources=doc_sources):
            results.append(
                RetrievalResult(
                    source_type=item.source_type,
                    authority=item.authority,
                    title=item.title,
                    location=item.location,
                    citation_url=item.citation_url,
                    text=item.text,
                    score=item.score,
                )
            )

    results = dedupe_retrieval_results(results)
    if "all" in normalized_sources:
        return diversify_retrieval_results(results, limit=limit)
    return sorted(results, key=lambda item: item.score)[:limit]


def dedupe_retrieval_results(results: list[RetrievalResult]) -> list[RetrievalResult]:
    deduped: list[RetrievalResult] = []
    seen: set[tuple[str, str, str]] = set()
    for result in sorted(results, key=lambda item: item.score):
        text_key = " ".join(result.text.lower().split())[:220]
        key = (result.source_type, result.citation_url, text_key)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(result)
    return deduped


def diversify_retrieval_results(
    results: list[RetrievalResult],
    *,
    limit: int,
) -> list[RetrievalResult]:
    sorted_results = sorted(results, key=lambda item: item.score)
    selected: list[RetrievalResult] = []
    selected_ids: set[int] = set()

    for source_type in ("manual", "community_tips", "companion", "video"):
        for index, result in enumerate(sorted_results):
            if result.source_type == source_type and index not in selected_ids:
                selected.append(result)
                selected_ids.add(index)
                break
        if len(selected) >= limit:
            return selected[:limit]

    for index, result in enumerate(sorted_results):
        if index in selected_ids:
            continue
        selected.append(result)
        if len(selected) >= limit:
            break

    return selected


def fallback_like_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int,
    lang: str | None,
) -> list[SearchResult]:
    terms = [term for term in query.split() if len(term) >= 2]
    if not terms:
        return []

    where = " OR ".join(["chunks.text LIKE ?" for _ in terms])
    params: list[object] = [f"%{term}%" for term in terms]
    if lang:
        where = f"({where}) AND chunks.lang = ?"
        params.append(lang)
    params.append(limit)

    rows = conn.execute(
        f"""
        SELECT
            videos.video_id,
            videos.title,
            videos.url,
            chunks.lang,
            chunks.start_ms,
            chunks.end_ms,
            chunks.text,
            0.0 AS score
        FROM chunks
        JOIN videos ON videos.video_id = chunks.video_id
        WHERE {where}
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [SearchResult(**dict(row)) for row in rows]


def fallback_doc_like_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    limit: int,
    sources: set[str] | None,
) -> list[DocChunk]:
    terms = [term for term in query.split() if len(term) >= 2]
    if not terms:
        return []

    where = " OR ".join(["doc_chunks.text LIKE ?" for _ in terms])
    params: list[object] = [f"%{term}%" for term in terms]
    if sources and "all" not in sources:
        placeholders = ", ".join(["?"] * len(sources))
        where = f"({where}) AND doc_chunks.source_type IN ({placeholders})"
        params.extend(sorted(sources))
    params.append(limit)

    rows = conn.execute(
        f"""
        SELECT
            documents.document_id,
            documents.source_type,
            documents.authority,
            documents.title,
            doc_chunks.location,
            doc_chunks.citation_url,
            doc_chunks.text,
            0.0 AS score
        FROM doc_chunks
        JOIN documents ON documents.document_id = doc_chunks.document_id
        WHERE {where}
        LIMIT ?
        """,
        params,
    ).fetchall()
    return [DocChunk(**dict(row)) for row in rows]


def make_fts_query(query: str) -> str:
    terms = [
        token.replace('"', "")
        for token in query.lower().split()
        if len(token.strip(".,!?;:()[]{}")) >= 2
    ]
    cleaned = [term.strip(".,!?;:()[]{}") for term in terms][:12]
    if not cleaned:
        return '""'
    return " OR ".join(f'"{term}"' for term in cleaned)
