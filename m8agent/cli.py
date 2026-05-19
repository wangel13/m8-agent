from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .db import connect, init_db, retrieve as retrieve_db, search as search_db
from .docs import DEFAULT_MANUAL_URL, DEFAULT_TIPS_URL, ingest_docs
from .llm import answer_with_llm
from .youtube import DEFAULT_CHANNEL_URL, ingest_channel


DEFAULT_RAW_DIR = Path("data/raw")
DEFAULT_RAW_DOCS_DIR = Path("data/raw_docs")
DEFAULT_DB_PATH = Path("data/m8agent.sqlite")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "ingest":
        return command_ingest(args)
    if args.command == "ingest-docs":
        return command_ingest_docs(args)
    if args.command == "search":
        return command_search(args)
    if args.command == "retrieve":
        return command_retrieve(args)
    if args.command == "ask":
        return command_ask(args)

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="m8agent")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    subparsers = parser.add_subparsers(dest="command")

    ingest = subparsers.add_parser("ingest", help="Download subtitles and build the local index.")
    ingest.add_argument("--channel-url", default=DEFAULT_CHANNEL_URL)
    ingest.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    ingest.add_argument("--langs", default="en.*,en,ru.*,ru")
    ingest.add_argument("--limit", type=int)
    ingest.add_argument("--no-auto-subs", action="store_true")
    ingest.add_argument("--no-download", action="store_true")
    ingest.add_argument("--cookies", type=Path)
    ingest.add_argument("--cookies-from-browser")
    ingest.add_argument("--js-runtime")
    ingest.add_argument(
        "--new-only",
        action="store_true",
        help="Download and index only videos that are not already in the database.",
    )

    ingest_docs_parser = subparsers.add_parser(
        "ingest-docs", help="Download and index the M8 manual and community tips."
    )
    ingest_docs_parser.add_argument("--raw-docs-dir", type=Path, default=DEFAULT_RAW_DOCS_DIR)
    ingest_docs_parser.add_argument("--manual-url", default=DEFAULT_MANUAL_URL)
    ingest_docs_parser.add_argument("--tips-url", default=DEFAULT_TIPS_URL)

    search = subparsers.add_parser("search", help="Search transcript chunks.")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=8)
    search.add_argument("--lang")

    retrieve = subparsers.add_parser("retrieve", help="Search videos and indexed documents.")
    retrieve.add_argument("query")
    retrieve.add_argument("--limit", type=int, default=8)
    retrieve.add_argument("--lang")
    retrieve.add_argument(
        "--sources",
        default="all",
        help="Comma-separated: all,video,manual,community_tips",
    )
    retrieve.add_argument("--format", choices=["text", "json"], default="text")

    ask = subparsers.add_parser("ask", help="Answer a question using transcript context.")
    ask.add_argument("question")
    ask.add_argument("--limit", type=int, default=8)
    ask.add_argument("--lang")

    return parser


def command_ingest(args: argparse.Namespace) -> int:
    videos, chunks = ingest_channel(
        channel_url=args.channel_url,
        raw_dir=args.raw_dir,
        db_path=args.db,
        languages=args.langs,
        include_auto_subs=not args.no_auto_subs,
        limit=args.limit,
        cookies=args.cookies,
        cookies_from_browser=args.cookies_from_browser,
        js_runtime=args.js_runtime,
        no_download=args.no_download,
        new_only=args.new_only,
    )
    print(f"Indexed {videos} videos and {chunks} transcript chunks into {args.db}")
    return 0


def command_ingest_docs(args: argparse.Namespace) -> int:
    stats = ingest_docs(
        db_path=args.db,
        raw_docs_dir=args.raw_docs_dir,
        manual_url=args.manual_url,
        tips_url=args.tips_url,
    )
    print(f"Indexed {stats.documents} documents and {stats.chunks} chunks into {args.db}")
    return 0


def command_search(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    init_db(conn)
    results = search_db(conn, args.query, limit=args.limit, lang=args.lang)
    conn.close()
    print_results(results)
    return 0


def command_retrieve(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    init_db(conn)
    results = retrieve_db(
        conn,
        args.query,
        limit=args.limit,
        sources=parse_sources(args.sources),
        lang=args.lang,
    )
    conn.close()

    if args.format == "json":
        print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2))
    else:
        print_retrieval_results(results)
    return 0


def command_ask(args: argparse.Namespace) -> int:
    conn = connect(args.db)
    init_db(conn)
    results = search_db(conn, args.question, limit=args.limit, lang=args.lang)
    conn.close()

    if not results:
        print("No matching transcript chunks found.")
        return 0

    answer = answer_with_llm(args.question, results)
    if answer:
        print(answer)
        print("\nSources:")
    else:
        print("LLM is not configured. Showing retrieved sources only.\n")

    print_results(results)
    return 0


def parse_sources(value: str) -> set[str]:
    allowed = {"all", "video", "manual", "community_tips"}
    sources = {item.strip() for item in value.split(",") if item.strip()}
    unknown = sources - allowed
    if unknown:
        raise SystemExit(f"Unknown sources: {', '.join(sorted(unknown))}")
    return sources or {"all"}


def print_results(results) -> None:
    for idx, result in enumerate(results, start=1):
        text = result.text
        if len(text) > 500:
            text = text[:497].rstrip() + "..."
        print(f"[{idx}] {result.title}")
        print(f"    {result.timestamp} {result.citation_url}")
        print(f"    lang={result.lang}")
        print(f"    {text}")
        print()


def print_retrieval_results(results) -> None:
    for idx, result in enumerate(results, start=1):
        text = result.text
        if len(text) > 500:
            text = text[:497].rstrip() + "..."
        print(f"[{idx}] {result.title}")
        print(f"    {result.source_type} authority={result.authority} location={result.location}")
        print(f"    {result.citation_url}")
        print(f"    {text}")
        print()


if __name__ == "__main__":
    sys.exit(main())
