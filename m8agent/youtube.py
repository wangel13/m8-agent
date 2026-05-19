from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile

from .db import (
    connect,
    get_video_ids,
    init_db,
    replace_chunks,
    upsert_video,
    video_from_info_json,
)
from .vtt import chunk_cues, parse_vtt


DEFAULT_CHANNEL_URL = "https://www.youtube.com/@Dirtywave/videos"


def download_subtitles(
    *,
    channel_url: str,
    raw_dir: Path,
    languages: str,
    include_auto_subs: bool,
    limit: int | None,
    cookies: Path | None,
    cookies_from_browser: str | None,
    js_runtime: str | None,
    download_archive: Path | None = None,
) -> None:
    raw_dir.mkdir(parents=True, exist_ok=True)
    if js_runtime is None and shutil.which("node"):
        js_runtime = "node"

    cmd = [
        sys.executable,
        "-m",
        "yt_dlp",
        "--ignore-errors",
        "--ignore-no-formats-error",
        "--skip-download",
        "--write-info-json",
        "--write-subs",
        "--sub-format",
        "vtt",
        "--sub-langs",
        languages,
        "-o",
        str(raw_dir / "%(id)s" / "%(id)s.%(ext)s"),
    ]
    if include_auto_subs:
        cmd.append("--write-auto-subs")
    if limit:
        cmd.extend(["--playlist-end", str(limit)])
    if cookies:
        cmd.extend(["--cookies", str(cookies)])
    if cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])
    if js_runtime:
        cmd.extend(["--js-runtimes", js_runtime])
    if download_archive:
        cmd.extend(["--download-archive", str(download_archive)])
    cmd.append(channel_url)

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(
            "yt-dlp finished with errors. Continuing with any subtitles that were downloaded.",
            file=sys.stderr,
        )


def index_raw_dir(
    *,
    raw_dir: Path,
    db_path: Path,
    video_ids: set[str] | None = None,
) -> tuple[int, int]:
    conn = connect(db_path)
    init_db(conn)

    video_count = 0
    chunk_count = 0
    for info_path in sorted(raw_dir.glob("*/*.info.json")):
        if video_ids is not None and info_path.parent.name not in video_ids:
            continue

        video = video_from_info_json(info_path)
        if video is None:
            continue
        if video_ids is not None and video.video_id not in video_ids:
            continue

        upsert_video(conn, video)
        video_count += 1

        for vtt_path in sorted(info_path.parent.glob("*.vtt")):
            lang = infer_lang(vtt_path, video.video_id)
            cues = parse_vtt(vtt_path.read_text(encoding="utf-8", errors="replace"))
            chunks = chunk_cues(cues)
            replace_chunks(
                conn,
                video_id=video.video_id,
                lang=lang,
                source_file=vtt_path,
                chunks=chunks,
            )
            chunk_count += len(chunks)

    conn.commit()
    conn.close()
    return video_count, chunk_count


def ingest_channel(
    *,
    channel_url: str,
    raw_dir: Path,
    db_path: Path,
    languages: str,
    include_auto_subs: bool,
    limit: int | None,
    cookies: Path | None,
    cookies_from_browser: str | None,
    js_runtime: str | None,
    no_download: bool,
    new_only: bool,
) -> tuple[int, int]:
    before = snapshot_video_dirs(raw_dir)
    archive_path: Path | None = None
    temp_dir: tempfile.TemporaryDirectory[str] | None = None

    if new_only and not no_download:
        temp_dir = tempfile.TemporaryDirectory(prefix="m8agent-archive-")
        archive_path = Path(temp_dir.name) / "downloaded.txt"
        write_download_archive(db_path=db_path, archive_path=archive_path)

    try:
        if not no_download:
            download_subtitles(
                channel_url=channel_url,
                raw_dir=raw_dir,
                languages=languages,
                include_auto_subs=include_auto_subs,
                limit=limit,
                cookies=cookies,
                cookies_from_browser=cookies_from_browser,
                js_runtime=js_runtime,
                download_archive=archive_path,
            )
        video_ids = changed_video_ids(raw_dir, before) if new_only else None
        if new_only and not video_ids:
            return (0, 0)
        return index_raw_dir(raw_dir=raw_dir, db_path=db_path, video_ids=video_ids)
    finally:
        if temp_dir is not None:
            temp_dir.cleanup()


def write_download_archive(*, db_path: Path, archive_path: Path) -> None:
    conn = connect(db_path)
    init_db(conn)
    video_ids = get_video_ids(conn)
    conn.close()
    archive_path.write_text(
        "".join(f"youtube {video_id}\n" for video_id in sorted(video_ids)),
        encoding="utf-8",
    )


def snapshot_video_dirs(raw_dir: Path) -> dict[str, float]:
    if not raw_dir.exists():
        return {}
    snapshot: dict[str, float] = {}
    for path in raw_dir.iterdir():
        if path.is_dir():
            snapshot[path.name] = newest_mtime(path)
    return snapshot


def changed_video_ids(raw_dir: Path, before: dict[str, float]) -> set[str]:
    changed: set[str] = set()
    for video_dir in raw_dir.iterdir() if raw_dir.exists() else []:
        if not video_dir.is_dir():
            continue
        if not list(video_dir.glob("*.info.json")):
            continue
        current_mtime = newest_mtime(video_dir)
        previous_mtime = before.get(video_dir.name)
        if previous_mtime is None or current_mtime > previous_mtime:
            changed.add(video_dir.name)
    return changed


def newest_mtime(path: Path) -> float:
    newest = path.stat().st_mtime
    for child in path.rglob("*"):
        try:
            newest = max(newest, child.stat().st_mtime)
        except FileNotFoundError:
            continue
    return newest


def infer_lang(path: Path, video_id: str) -> str:
    name = path.name
    match = re.match(rf"{re.escape(video_id)}\.(?P<lang>.+)\.vtt$", name)
    if match:
        return match.group("lang")
    parts = path.stem.split(".")
    return parts[-1] if len(parts) > 1 else "unknown"
