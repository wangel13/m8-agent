from __future__ import annotations

from dataclasses import dataclass
from html import unescape
import re


TIMESTAMP_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})\s+-->\s+"
    r"(?P<end>\d{2}:\d{2}:\d{2}[.,]\d{3}|\d{2}:\d{2}[.,]\d{3})"
)
TAG_RE = re.compile(r"<[^>]+>")
INLINE_TIMESTAMP_RE = re.compile(r"<\d{2}:\d{2}:\d{2}[.,]\d{3}>")


@dataclass(frozen=True)
class Cue:
    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True)
class Chunk:
    start_ms: int
    end_ms: int
    text: str


def parse_timestamp(value: str) -> int:
    value = value.replace(",", ".")
    parts = value.split(":")
    if len(parts) == 2:
        hours = 0
        minutes, seconds = parts
    elif len(parts) == 3:
        hours, minutes, seconds = parts
    else:
        raise ValueError(f"Invalid timestamp: {value}")

    seconds_int, milliseconds = seconds.split(".")
    return (
        int(hours) * 3_600_000
        + int(minutes) * 60_000
        + int(seconds_int) * 1_000
        + int(milliseconds)
    )


def clean_text(text: str) -> str:
    text = INLINE_TIMESTAMP_RE.sub(" ", text)
    text = TAG_RE.sub(" ", text)
    text = unescape(text)
    text = re.sub(r"\s+", " ", text)
    return collapse_repeated_sequences(text.strip())


def collapse_repeated_sequences(text: str, *, max_window: int = 16) -> str:
    tokens = text.split()
    if len(tokens) < 2:
        return text

    normalized = [_normalize_token(token) for token in tokens]
    result: list[str] = []
    i = 0
    while i < len(tokens):
        remaining = len(tokens) - i
        window = min(max_window, remaining // 2)
        repeated_window = 0
        for size in range(window, 0, -1):
            current = normalized[i : i + size]
            following = normalized[i + size : i + (2 * size)]
            if current and current == following:
                repeated_window = size
                break

        if repeated_window:
            result.extend(tokens[i : i + repeated_window])
            i += repeated_window
            while normalized[i : i + repeated_window] == normalized[
                i - repeated_window : i
            ]:
                i += repeated_window
            continue

        result.append(tokens[i])
        i += 1

    collapsed = " ".join(result)
    return collapsed if collapsed == text else collapse_repeated_sequences(collapsed)


def _normalize_token(token: str) -> str:
    return token.strip(".,!?;:()[]{}\"'").lower()


def parse_vtt(content: str) -> list[Cue]:
    lines = content.replace("\ufeff", "").splitlines()
    cues: list[Cue] = []
    i = 0

    while i < len(lines):
        match = TIMESTAMP_RE.search(lines[i])
        if not match:
            i += 1
            continue

        start_ms = parse_timestamp(match.group("start"))
        end_ms = parse_timestamp(match.group("end"))
        i += 1

        text_lines: list[str] = []
        while i < len(lines) and lines[i].strip():
            text_lines.append(lines[i])
            i += 1

        text = clean_text(" ".join(text_lines))
        if text:
            cues.append(Cue(start_ms=start_ms, end_ms=end_ms, text=text))

        i += 1

    return dedupe_adjacent_cues(cues)


def dedupe_adjacent_cues(cues: list[Cue]) -> list[Cue]:
    deduped: list[Cue] = []
    previous_text = None
    for cue in cues:
        if cue.text == previous_text:
            continue
        deduped.append(cue)
        previous_text = cue.text
    return deduped


def chunk_cues(
    cues: list[Cue],
    *,
    max_chars: int = 1_200,
    max_seconds: int = 90,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    current: list[Cue] = []

    for cue in cues:
        if not current:
            current.append(cue)
            continue

        candidate_text = " ".join([item.text for item in current] + [cue.text])
        candidate_seconds = (cue.end_ms - current[0].start_ms) / 1000
        if len(candidate_text) > max_chars or candidate_seconds > max_seconds:
            chunks.append(_make_chunk(current))
            current = [cue]
        else:
            current.append(cue)

    if current:
        chunks.append(_make_chunk(current))

    return chunks


def _make_chunk(cues: list[Cue]) -> Chunk:
    return Chunk(
        start_ms=cues[0].start_ms,
        end_ms=cues[-1].end_ms,
        text=clean_text(" ".join(cue.text for cue in cues)),
    )


def format_timestamp(ms: int) -> str:
    total_seconds = ms // 1000
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
