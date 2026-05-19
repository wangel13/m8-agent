# Dirtywave M8 Agent

A local retrieval assistant for Dirtywave M8 questions. It indexes Dirtywave YouTube meetup transcripts, the official M8 operation manual, and the Open M8 Tips Tricks and Findings document, then returns source-backed results with timestamps, page links, or section labels.

This is an unofficial project. It is not affiliated with, sponsored by, or endorsed by Dirtywave LLC.

The project has three main jobs:

1. Download YouTube metadata and subtitles from `https://www.youtube.com/@Dirtywave/videos`.
2. Index transcripts and documents in a local SQLite FTS database.
3. Retrieve relevant M8 references for Codex or, optionally, generate answers through an OpenAI-compatible chat endpoint.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

`yt-dlp` and `pypdf` are installed as project dependencies.

## Ingest YouTube Transcripts

Download subtitles and build the transcript index:

```bash
m8agent ingest --channel-url https://www.youtube.com/@Dirtywave/videos
```

If YouTube asks you to sign in or shows `Sign in to confirm you're not a bot`, pass browser cookies:

```bash
m8agent ingest --channel-url https://www.youtube.com/@Dirtywave/videos --cookies-from-browser chrome
```

You can also use a cookies file:

```bash
m8agent ingest --channel-url https://www.youtube.com/@Dirtywave/videos --cookies cookies.txt
```

For a small test run:

```bash
m8agent ingest --channel-url https://www.youtube.com/@Dirtywave/videos --limit 5
```

Download and index only videos that are not already present in the local database:

```bash
m8agent ingest --channel-url https://www.youtube.com/@Dirtywave/videos --new-only --cookies-from-browser chrome
```

`--new-only` uses the `video_id` values already stored in `data/m8agent.sqlite` to skip known videos during the YouTube download step, then indexes only newly downloaded video folders. This is the preferred update command after a new Dirtywave video appears on the channel.

Rebuild the index from already downloaded subtitles:

```bash
m8agent ingest --no-download
```

## Ingest Manual and Open M8 Tips

Download and index the official Dirtywave M8 operation manual and the community Open M8 Tips Tricks and Findings document:

```bash
m8agent ingest-docs
```

Defaults:

- Official manual: M8 Operation Manual v6.5.2, 2026-04-21
- Community tips: Open M8 Tips Tricks and Findings Google Doc export

Raw documents are stored locally under `data/raw_docs/`. They are ignored by git.

## Search and Retrieve

Search only YouTube transcript chunks:

```bash
m8agent search "tables chord progression"
```

Retrieve from all indexed sources:

```bash
m8agent retrieve "table command modulation" --format json --limit 5
```

Limit retrieval to one source type:

```bash
m8agent retrieve "time stretching loops" --sources manual
m8agent retrieve "template song utility tables" --sources community_tips
m8agent retrieve "USB audio multi-channel AUM iPad" --sources video --lang en
```

`retrieve` returns unified results with:

- `source_type`: `video`, `manual`, or `community_tips`
- `authority`: `official` or `community`
- `title`
- `location`: timestamp, page, or section heading
- `citation_url`
- `text`
- `score`

## Optional LLM Answers

The `ask` command can call an OpenAI-compatible Chat Completions endpoint:

```bash
export OPENAI_API_KEY="..."
export M8AGENT_MODEL="gpt-4.1-mini"
```

Optionally set a different endpoint:

```bash
export OPENAI_BASE_URL="https://api.openai.com/v1"
```

Then run:

```bash
m8agent ask "How do I make a chord progression on M8?"
```

If `OPENAI_API_KEY` or `M8AGENT_MODEL` is not set, `ask` falls back to showing retrieved sources only.

## Using the Codex Skill

This repository includes a repo-local Codex skill at:

```text
skills/dirtywave-m8/SKILL.md
```

The skill tells Codex to use `m8agent retrieve` before answering factual Dirtywave M8 questions. The intended workflow is:

1. Codex runs retrieval from the repo root:

   ```bash
   .venv/bin/m8agent retrieve "<question>" --format json --limit 8
   ```

2. Codex writes the final answer itself, in the same language as the user.
3. Codex treats `authority=official` manual results as official reference material.
4. Codex treats `authority=community` tips and meetup videos as practical community knowledge.
5. If the official manual and community tips conflict, Codex should show both versions explicitly instead of silently choosing one.

Example manual invocation:

```bash
.venv/bin/m8agent retrieve "How do tables work for modulation on M8?" --format json --limit 8
```

### Making the Skill Available Globally

In this repo, the skill is versioned locally only. To make Codex auto-discover it in future sessions on this machine, copy or symlink it into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
cp -R skills/dirtywave-m8 ~/.codex/skills/
```

After that, new Codex sessions should list `dirtywave-m8` as an available skill, depending on your Codex build and skill loading behavior.

## Data Layout

- `data/raw/` - downloaded YouTube `.info.json` and `.vtt` files.
- `data/raw_docs/` - downloaded manual and tips document snapshots.
- `data/m8agent.sqlite` - local SQLite FTS index.

## Limitations

- YouTube auto-subtitles can contain transcription errors, repeated phrases, or wrong M8 terminology.
- The project downloads metadata, subtitles, and reference documents, not YouTube videos.
- Raw documents and SQLite indexes are local data under `data/` and are not committed.
- Respect YouTube, Dirtywave, Google Docs, and community document terms when using the downloaded materials.
