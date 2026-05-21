import { mkdtempSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import Database from "better-sqlite3";
import { describe, expect, it } from "vitest";

import { openM8Database } from "#/server/db";
import { getM8Stats, retrieveM8 } from "#/server/retrieval";

describe("M8 retrieval", () => {
	it("returns timestamped video results", () => {
		const dbPath = createFixture();
		const db = openM8Database(dbPath);

		const results = retrieveM8(db, {
			query: "table modulation",
			limit: 5,
			sources: ["video"],
		});

		db.close();

		expect(results).toHaveLength(1);
		expect(results[0]).toMatchObject({
			source_type: "video",
			authority: "community",
			location: "1:05",
			citation_url: "https://www.youtube.com/watch?v=test&t=65s",
		});
	});

	it("returns companion document results", () => {
		const dbPath = createFixture();
		const db = openM8Database(dbPath);

		const results = retrieveM8(db, {
			query: "sampler slicing",
			limit: 5,
			sources: ["companion"],
		});

		db.close();

		expect(results[0]).toMatchObject({
			source_type: "companion",
			authority: "community",
			title: "The M8 Companion",
			location: "5.3 Slicing made easy",
		});
	});

	it("diversifies all-source results", () => {
		const dbPath = createFixture();
		const db = openM8Database(dbPath);

		const results = retrieveM8(db, {
			query: "table",
			limit: 4,
			sources: ["all"],
		});

		db.close();

		expect(results.map((result) => result.source_type)).toContain("manual");
		expect(results.map((result) => result.source_type)).toContain("video");
	});

	it("opens the database in read-only mode", () => {
		const dbPath = createFixture();
		const db = openM8Database(dbPath);

		expect(() => {
			db.prepare(
				"INSERT INTO videos(video_id, title, url) VALUES (?, ?, ?)",
			).run("new", "New", "https://example.com");
		}).toThrow();

		db.close();
	});

	it("returns stats", () => {
		const dbPath = createFixture();
		const db = openM8Database(dbPath);

		const stats = getM8Stats(db);

		db.close();

		expect(stats.videos).toBe(1);
		expect("database_path" in stats).toBe(false);
		expect(stats.document_chunks_by_source).toEqual([
			{ source_type: "companion", chunks: 1 },
			{ source_type: "manual", chunks: 1 },
		]);
	});
});

function createFixture(): string {
	const dir = mkdtempSync(join(tmpdir(), "m8-webapp-"));
	const dbPath = join(dir, "m8agent.sqlite");
	const db = new Database(dbPath);

	db.exec(`
    CREATE TABLE videos (
      video_id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      url TEXT NOT NULL,
      upload_date TEXT,
      duration INTEGER,
      channel TEXT,
      description TEXT
    );

    CREATE TABLE chunks (
      id INTEGER PRIMARY KEY,
      video_id TEXT NOT NULL REFERENCES videos(video_id),
      lang TEXT NOT NULL,
      start_ms INTEGER NOT NULL,
      end_ms INTEGER NOT NULL,
      text TEXT NOT NULL,
      source_file TEXT NOT NULL
    );

    CREATE VIRTUAL TABLE chunks_fts
    USING fts5(text, content='chunks', content_rowid='id', tokenize='unicode61');

    CREATE TABLE documents (
      document_id TEXT PRIMARY KEY,
      title TEXT NOT NULL,
      source_type TEXT NOT NULL,
      authority TEXT NOT NULL,
      url TEXT NOT NULL,
      version TEXT
    );

    CREATE TABLE doc_chunks (
      id INTEGER PRIMARY KEY,
      document_id TEXT NOT NULL REFERENCES documents(document_id),
      source_type TEXT NOT NULL,
      authority TEXT NOT NULL,
      location TEXT NOT NULL,
      citation_url TEXT NOT NULL,
      text TEXT NOT NULL,
      source_file TEXT NOT NULL
    );

    CREATE VIRTUAL TABLE doc_chunks_fts
    USING fts5(text, content='doc_chunks', content_rowid='id', tokenize='unicode61');
  `);

	db.prepare("INSERT INTO videos(video_id, title, url) VALUES (?, ?, ?)").run(
		"test",
		"M8 Table Tutorial",
		"https://www.youtube.com/watch?v=test",
	);
	db.prepare(
		`
    INSERT INTO chunks(video_id, lang, start_ms, end_ms, text, source_file)
    VALUES (?, ?, ?, ?, ?, ?)
    `,
	).run("test", "en", 65_000, 70_000, "table modulation workflow", "test.vtt");
	db.prepare("INSERT INTO chunks_fts(rowid, text) VALUES (?, ?)").run(
		1,
		"table modulation workflow",
	);

	db.prepare(
		`
    INSERT INTO documents(document_id, title, source_type, authority, url)
    VALUES (?, ?, ?, ?, ?)
    `,
	).run(
		"manual",
		"M8 Operation Manual",
		"manual",
		"official",
		"https://manual.test",
	);
	db.prepare(
		`
    INSERT INTO documents(document_id, title, source_type, authority, url)
    VALUES (?, ?, ?, ?, ?)
    `,
	).run(
		"companion",
		"The M8 Companion",
		"companion",
		"community",
		"https://companion.test",
	);

	insertDocChunk(
		db,
		1,
		"manual",
		"manual",
		"official",
		"p. 31",
		"table tick reference",
	);
	insertDocChunk(
		db,
		2,
		"companion",
		"companion",
		"community",
		"5.3 Slicing made easy",
		"sampler slicing workflow",
	);

	db.close();
	return dbPath;
}

function insertDocChunk(
	db: Database.Database,
	id: number,
	documentId: string,
	sourceType: string,
	authority: string,
	location: string,
	text: string,
) {
	db.prepare(
		`
    INSERT INTO doc_chunks(
      id,
      document_id,
      source_type,
      authority,
      location,
      citation_url,
      text,
      source_file
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `,
	).run(
		id,
		documentId,
		sourceType,
		authority,
		location,
		"https://source.test",
		text,
		"doc.txt",
	);
	db.prepare("INSERT INTO doc_chunks_fts(rowid, text) VALUES (?, ?)").run(
		id,
		text,
	);
}
