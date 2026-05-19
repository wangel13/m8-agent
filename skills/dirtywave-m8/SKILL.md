---
name: dirtywave-m8
description: Use this skill when answering questions about the Dirtywave M8 tracker, M8 workflow, instruments, tables, FX commands, sampling, song writing, shortcuts, firmware behavior, Dirtywave meetup videos, the M8 operation manual, or Open M8 Tips Tricks and Findings.
---

# Dirtywave M8

Use the local `m8agent` retrieval index before answering factual Dirtywave M8 questions.

## Retrieval

From the repository root, run:

```bash
.venv/bin/m8agent retrieve "<user question>" --format json --limit 8
```

Use `--lang en` when searching meetup transcript content. Use `--sources manual`, `--sources community_tips`, or `--sources video` only when the user asks for a specific source type.

## Answering

- Answer in the same language the user used.
- Treat `authority=official` manual results as official reference material.
- Treat `authority=community` tips and videos as practical community knowledge.
- For factual answers, include citations with the provided `citation_url`.
- For creative coaching, cite only the most relevant sources and keep the answer practical.
- If official manual results and community tips disagree, explicitly describe both: "The manual says..." and "Community tips say...".
- If retrieval returns weak or irrelevant results, say what is missing instead of inventing M8 behavior.

## Citation Format

Use compact source labels:

- `Official manual, p. 24: <url>`
- `Open M8 Tips, <heading>: <url>`
- `Meetup video, 01:22:59: <url>`
