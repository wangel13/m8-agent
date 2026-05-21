import type {
	M8Source,
	RetrievalResult,
	SearchRequest,
	StatsResult,
} from "#/lib/m8-schemas";
import type { M8Database } from "#/server/db";
import { withM8Database } from "#/server/db";

type VideoRow = {
	title: string;
	url: string;
	lang: string;
	start_ms: number;
	end_ms: number;
	text: string;
	score: number;
};

type DocRow = {
	source_type: RetrievalResult["source_type"];
	authority: string;
	title: string;
	location: string;
	citation_url: string;
	text: string;
	score: number;
};

const DOC_SOURCES = ["manual", "community_tips", "companion"] as const;

export function retrieveM8(
	db: M8Database,
	request: SearchRequest,
): RetrievalResult[] {
	const normalizedSources = normalizeSources(request.sources);
	const results: RetrievalResult[] = [];

	if (normalizedSources.has("all") || normalizedSources.has("video")) {
		const videoLimit =
			normalizedSources.size === 1 && normalizedSources.has("video")
				? request.limit
				: Math.max(request.limit, 12);

		for (const row of searchVideos(
			db,
			request.query,
			videoLimit,
			request.lang,
		)) {
			results.push({
				source_type: "video",
				authority: "community",
				title: row.title,
				location: formatTimestamp(row.start_ms),
				citation_url: videoCitationUrl(row.url, row.start_ms),
				text: row.text,
				score: row.score,
			});
		}
	}

	const docSources = getDocumentSources(normalizedSources);
	if (docSources.length > 0) {
		const docOnly = [...normalizedSources].every((source) =>
			DOC_SOURCES.includes(source as (typeof DOC_SOURCES)[number]),
		);
		const docLimit = docOnly ? request.limit : Math.max(request.limit, 12);

		for (const row of searchDocuments(
			db,
			request.query,
			docLimit,
			docSources,
		)) {
			results.push({
				source_type: row.source_type,
				authority: row.authority,
				title: row.title,
				location: row.location,
				citation_url: row.citation_url,
				text: row.text,
				score: row.score,
			});
		}
	}

	const deduped = dedupeResults(results);
	if (normalizedSources.has("all")) {
		return diversifyResults(deduped, request.limit);
	}
	return deduped.sort(byScore).slice(0, request.limit);
}

export function retrieveM8FromDefaultDb(
	request: SearchRequest,
): RetrievalResult[] {
	return withM8Database((db) => retrieveM8(db, request));
}

export function getM8Stats(db: M8Database): StatsResult {
	return {
		videos: count(db, "videos"),
		transcript_chunks: count(db, "chunks"),
		documents: count(db, "documents"),
		document_chunks: count(db, "doc_chunks"),
		document_chunks_by_source: db
			.prepare(
				`
        SELECT source_type, COUNT(*) AS chunks
        FROM doc_chunks
        GROUP BY source_type
        ORDER BY source_type
        `,
			)
			.all() as StatsResult["document_chunks_by_source"],
	};
}

export function getM8StatsFromDefaultDb(): StatsResult {
	return withM8Database((db) => getM8Stats(db));
}

function searchVideos(
	db: M8Database,
	query: string,
	limit: number,
	lang?: string,
): VideoRow[] {
	const ftsQuery = makeFtsQuery(query);
	const langClause = lang ? "AND chunks.lang = ?" : "";
	const params: Array<string | number> = lang
		? [ftsQuery, lang, limit]
		: [ftsQuery, limit];

	try {
		return db
			.prepare(
				`
        SELECT
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
        WHERE chunks_fts MATCH ? ${langClause}
        ORDER BY score
        LIMIT ?
        `,
			)
			.all(...params) as VideoRow[];
	} catch {
		return fallbackVideoSearch(db, query, limit, lang);
	}
}

function searchDocuments(
	db: M8Database,
	query: string,
	limit: number,
	sources: string[],
): DocRow[] {
	const ftsQuery = makeFtsQuery(query);
	const sourceClause =
		sources.length > 0
			? `AND doc_chunks.source_type IN (${sources.map(() => "?").join(", ")})`
			: "";
	const params: Array<string | number> = [ftsQuery, ...sources, limit];

	try {
		return db
			.prepare(
				`
        SELECT
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
        WHERE doc_chunks_fts MATCH ? ${sourceClause}
        ORDER BY score
        LIMIT ?
        `,
			)
			.all(...params) as DocRow[];
	} catch {
		return fallbackDocumentSearch(db, query, limit, sources);
	}
}

function fallbackVideoSearch(
	db: M8Database,
	query: string,
	limit: number,
	lang?: string,
): VideoRow[] {
	const terms = likeTerms(query);
	if (terms.length === 0) {
		return [];
	}

	const where = terms.map(() => "chunks.text LIKE ?").join(" OR ");
	const langClause = lang ? "AND chunks.lang = ?" : "";
	const params: Array<string | number> = terms.map((term) => `%${term}%`);
	if (lang) {
		params.push(lang);
	}
	params.push(limit);

	return db
		.prepare(
			`
      SELECT
        videos.title,
        videos.url,
        chunks.lang,
        chunks.start_ms,
        chunks.end_ms,
        chunks.text,
        0.0 AS score
      FROM chunks
      JOIN videos ON videos.video_id = chunks.video_id
      WHERE (${where}) ${langClause}
      LIMIT ?
      `,
		)
		.all(...params) as VideoRow[];
}

function fallbackDocumentSearch(
	db: M8Database,
	query: string,
	limit: number,
	sources: string[],
): DocRow[] {
	const terms = likeTerms(query);
	if (terms.length === 0) {
		return [];
	}

	const where = terms.map(() => "doc_chunks.text LIKE ?").join(" OR ");
	const sourceClause =
		sources.length > 0
			? `AND doc_chunks.source_type IN (${sources.map(() => "?").join(", ")})`
			: "";
	const params: Array<string | number> = [
		...terms.map((term) => `%${term}%`),
		...sources,
		limit,
	];

	return db
		.prepare(
			`
      SELECT
        documents.source_type,
        documents.authority,
        documents.title,
        doc_chunks.location,
        doc_chunks.citation_url,
        doc_chunks.text,
        0.0 AS score
      FROM doc_chunks
      JOIN documents ON documents.document_id = doc_chunks.document_id
      WHERE (${where}) ${sourceClause}
      LIMIT ?
      `,
		)
		.all(...params) as DocRow[];
}

function normalizeSources(sources: M8Source[]): Set<M8Source> {
	if (sources.includes("all")) {
		return new Set(["all"]);
	}
	return new Set(sources);
}

function getDocumentSources(sources: Set<M8Source>): string[] {
	if (sources.has("all")) {
		return [...DOC_SOURCES];
	}
	return [...sources].filter((source) =>
		DOC_SOURCES.includes(source as (typeof DOC_SOURCES)[number]),
	);
}

function dedupeResults(results: RetrievalResult[]): RetrievalResult[] {
	const selected: RetrievalResult[] = [];
	const seen = new Set<string>();

	for (const result of results.sort(byScore)) {
		const textKey = result.text
			.toLowerCase()
			.split(/\s+/)
			.join(" ")
			.slice(0, 220);
		const key = `${result.source_type}\n${result.citation_url}\n${textKey}`;
		if (seen.has(key)) {
			continue;
		}
		seen.add(key);
		selected.push(result);
	}

	return selected;
}

function diversifyResults(
	results: RetrievalResult[],
	limit: number,
): RetrievalResult[] {
	const sorted = [...results].sort(byScore);
	const selected: RetrievalResult[] = [];
	const selectedIndexes = new Set<number>();

	for (const sourceType of ["manual", "community_tips", "companion", "video"]) {
		const index = sorted.findIndex(
			(result, resultIndex) =>
				result.source_type === sourceType && !selectedIndexes.has(resultIndex),
		);
		if (index >= 0) {
			selected.push(sorted[index]);
			selectedIndexes.add(index);
		}
		if (selected.length >= limit) {
			return selected.slice(0, limit);
		}
	}

	for (const [index, result] of sorted.entries()) {
		if (selectedIndexes.has(index)) {
			continue;
		}
		selected.push(result);
		if (selected.length >= limit) {
			break;
		}
	}

	return selected;
}

function makeFtsQuery(query: string): string {
	const cleaned = query
		.toLowerCase()
		.split(/\s+/)
		.map((token) =>
			token
				.replaceAll('"', "")
				.replace(/^[.,!?;:()[\]{}]+|[.,!?;:()[\]{}]+$/g, ""),
		)
		.filter((token) => token.length >= 2)
		.slice(0, 12);

	if (cleaned.length === 0) {
		return '""';
	}

	return cleaned.map((term) => `"${term}"`).join(" OR ");
}

function likeTerms(query: string): string[] {
	return query
		.split(/\s+/)
		.map((term) => term.trim())
		.filter((term) => term.length >= 2);
}

function formatTimestamp(ms: number): string {
	const totalSeconds = Math.floor(ms / 1000);
	const hours = Math.floor(totalSeconds / 3600);
	const minutes = Math.floor((totalSeconds % 3600) / 60);
	const seconds = totalSeconds % 60;

	if (hours > 0) {
		return `${hours}:${pad(minutes)}:${pad(seconds)}`;
	}
	return `${minutes}:${pad(seconds)}`;
}

function videoCitationUrl(url: string, startMs: number): string {
	const separator = url.includes("?") ? "&" : "?";
	return `${url}${separator}t=${Math.floor(startMs / 1000)}s`;
}

function count(db: M8Database, table: string): number {
	const row = db.prepare(`SELECT COUNT(*) AS count FROM ${table}`).get() as {
		count: number;
	};
	return row.count;
}

function byScore(a: RetrievalResult, b: RetrievalResult): number {
	return a.score - b.score;
}

function pad(value: number): string {
	return String(value).padStart(2, "0");
}
