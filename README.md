# Dirtywave M8 Agent

A local retrieval assistant for Dirtywave M8 questions. It indexes Dirtywave YouTube meetup transcripts, the official M8 operation manual, the Open M8 Tips Tricks and Findings document, and The M8 Companion, then returns source-backed results with timestamps, page links, or section labels.

This is an unofficial project. It is not affiliated with, sponsored by, or endorsed by Dirtywave LLC.

The project has three main jobs:

1. Download YouTube metadata and subtitles from Dirtywave M8 videos, playlists, and channels.
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

Download subtitles from the default Dirtywave channel and build the transcript index:

```bash
m8agent ingest
```

You can ingest any mix of YouTube channels, playlists, and individual videos:

```bash
m8agent ingest \
  --url https://www.youtube.com/@Dirtywave/videos \
  --url https://www.youtube.com/playlist?list=PLAYLIST_ID \
  --url https://www.youtube.com/watch?v=VIDEO_ID
```

For a larger source list, put one URL per line in a text file:

```text
# m8-sources.txt
https://www.youtube.com/@Dirtywave/videos
https://www.youtube.com/playlist?list=PLAYLIST_ID
https://www.youtube.com/watch?v=VIDEO_ID
```

Then run:

```bash
m8agent ingest --urls-file m8-sources.txt
```

`--channel-url` is still supported for compatibility:

```bash
m8agent ingest --channel-url https://www.youtube.com/@Dirtywave/videos
```

If YouTube asks you to sign in or shows `Sign in to confirm you're not a bot`, pass browser cookies:

```bash
m8agent ingest --urls-file m8-sources.txt --cookies-from-browser chrome
```

You can also use a cookies file:

```bash
m8agent ingest --channel-url https://www.youtube.com/@Dirtywave/videos --cookies cookies.txt
```

For a small test run:

```bash
m8agent ingest --urls-file m8-sources.txt --limit 5
```

When multiple sources are provided, `--limit` applies to each playlist or channel source.

Download and index only videos that are not already present in the local database:

```bash
m8agent ingest --urls-file m8-sources.txt --new-only --cookies-from-browser chrome
```

`--new-only` uses the `video_id` values already stored in `data/m8agent.sqlite` to skip known videos during the YouTube download step, then indexes only newly downloaded video folders. This is the preferred update command after a new video appears in any configured channel or playlist.

Rebuild the index from already downloaded subtitles:

```bash
m8agent ingest --no-download
```

## Ingest Reference Documents

Download and index the official Dirtywave M8 operation manual and the community Open M8 Tips Tricks and Findings document:

```bash
m8agent ingest-docs
```

Defaults:

- Official manual: M8 Operation Manual v6.5.2, 2026-04-21
- Community tips: Open M8 Tips Tricks and Findings Google Doc export

Download and index The M8 Companion HTML tutorial:

```bash
m8agent ingest-companion
```

Default:

- The M8 Companion: https://cs.uwaterloo.ca/~plragde/flaneries/TM8C/

Raw documents are stored locally under `data/raw_docs/`. They are ignored by git. The M8 Companion is written by Prabhakar Ragde and Brian Simpson and is licensed under CC BY-NC-SA 4.0; this project stores only local snapshots for retrieval and cites the original pages in results.

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
m8agent retrieve "sampler slicing workflow" --sources companion
m8agent retrieve "USB audio multi-channel AUM iPad" --sources video --lang en
```

`retrieve` returns unified results with:

- `source_type`: `video`, `manual`, `community_tips`, or `companion`
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

## Web App and MCP Server

The `web-app/` directory contains a TanStack Start app for searching the existing SQLite index without Python. It opens `data/m8agent.sqlite` through `better-sqlite3` in read-only mode and exposes both a browser UI and MCP tools.

```bash
cd web-app
pnpm install
M8_AUTH_TOKEN="change-me" pnpm dev
```

Open `http://localhost:3000` and enter the same token. For a public read-only search site, run with `M8_PUBLIC_SEARCH=true`; `/mcp` still requires `M8_AUTH_TOKEN`. The app also exposes:

- `POST /api/search`
- `GET /api/stats`
- `POST /mcp` for HTTP MCP clients
- `pnpm mcp` for local stdio MCP clients

See `web-app/README.md` for environment variables and MCP examples.

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
4. Codex treats `authority=community` tips, The M8 Companion, and meetup videos as practical community knowledge.
5. If the official manual and community sources conflict, Codex should show both versions explicitly instead of silently choosing one.

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
- `data/raw_docs/` - downloaded manual, tips, and The M8 Companion document snapshots.
- `data/m8agent.sqlite` - local SQLite FTS index.

## Limitations

- YouTube auto-subtitles can contain transcription errors, repeated phrases, or wrong M8 terminology.
- The project downloads metadata, subtitles, and reference documents, not YouTube videos.
- Raw documents and SQLite indexes are local data under `data/` and are not committed.
- Respect YouTube, Dirtywave, Google Docs, The M8 Companion, and community document terms when using the downloaded materials.
