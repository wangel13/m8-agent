# M8 Agent Web App

TanStack Start app for searching a local `m8agent.sqlite` index and exposing the same retrieval through MCP.

The app is read-only. It does not ingest sources, create migrations, or call Python. Build the SQLite index from the repository root with the existing Python CLI first.

## Setup

```bash
pnpm install
```

Create `.env` in `web-app/`:

```bash
M8_AUTH_TOKEN="change-me"
# Optional. Set to true to make /api/search and /api/stats public.
M8_PUBLIC_SEARCH="false"
# Optional. Build-time flag for the browser UI. Keep it aligned with M8_PUBLIC_SEARCH.
VITE_PUBLIC_SEARCH="false"
# Optional. Defaults to ../data/m8agent.sqlite when running from web-app/.
M8_DB_PATH="../data/m8agent.sqlite"
# Optional. Set only when a browser from another origin must call the API.
M8_CORS_ORIGIN="http://localhost:3000"
```

If `better-sqlite3` build scripts were blocked by pnpm:

```bash
pnpm approve-builds
pnpm rebuild better-sqlite3
```

## Run

```bash
pnpm dev
```

Open `http://localhost:3000`. If `M8_PUBLIC_SEARCH` is not `true`, enter the same token as `M8_AUTH_TOKEN`, then search.

## HTTP API

By default, search and stats endpoints require:

```text
Authorization: Bearer <M8_AUTH_TOKEN>
```

When `M8_PUBLIC_SEARCH=true`, `/api/search` and `/api/stats` are public and should be protected by your hosting layer with rate limiting. The stats response never includes the local SQLite path.

Search:

```bash
curl -X POST http://localhost:3000/api/search \
  -H "Authorization: Bearer $M8_AUTH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query":"USB audio options","sources":["all"],"limit":8}'
```

Stats:

```bash
curl http://localhost:3000/api/stats \
  -H "Authorization: Bearer $M8_AUTH_TOKEN"
```

## MCP

HTTP endpoint:

```text
http://localhost:3000/mcp
```

The HTTP MCP endpoint also requires the bearer token.

`/mcp` always requires `Authorization: Bearer <M8_AUTH_TOKEN>`, even when `M8_PUBLIC_SEARCH=true`.

Local stdio MCP:

```bash
pnpm mcp
```

Available MCP tools:

- `search_m8` with `{ query, limit?, sources?, lang? }`
- `get_m8_stats`

`search_m8` instructs MCP clients to answer in the user's language, use retrieved results for factual Dirtywave M8 claims, and include a final `Sources` section with compact labels and each result's `citation_url`.

## Deploy With Coolify

Use the Dockerfile build pack and set the application base directory to `web-app`.

Required runtime variables:

```bash
M8_AUTH_TOKEN="replace-with-a-long-random-token"
M8_DB_PATH="/data/m8agent.sqlite"
```

For a public read-only search site, also set:

```bash
M8_PUBLIC_SEARCH="true"
VITE_PUBLIC_SEARCH="true"
```

`VITE_PUBLIC_SEARCH` is read by the browser bundle at build time. In Coolify, mark it as a build variable or rebuild the app after changing it. `/mcp` still requires `M8_AUTH_TOKEN` even when search is public.

Optional runtime variable:

```bash
M8_CORS_ORIGIN="https://your-domain.example"
```

Add persistent storage in Coolify and mount it at `/data`, then upload or copy your prepared SQLite index to:

```text
/data/m8agent.sqlite
```

The container listens on port `3000` and starts with:

```bash
node .output/server/index.mjs
```

You can test the production image locally:

```bash
docker build --build-arg VITE_PUBLIC_SEARCH=true -t m8-agent-web .
docker run --rm -p 3000:3000 \
  -e M8_AUTH_TOKEN="change-me" \
  -e M8_PUBLIC_SEARCH="true" \
  -e M8_DB_PATH="/data/m8agent.sqlite" \
  -v "$(pwd)/../data:/data:ro" \
  m8-agent-web
```

## Checks

```bash
pnpm check
pnpm typecheck
pnpm test
pnpm build
```
