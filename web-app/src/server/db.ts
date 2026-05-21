import Database from "better-sqlite3";

import { getDatabasePath } from "#/server/config";

export type M8Database = Database.Database;

export function openM8Database(dbPath = getDatabasePath()): M8Database {
	const db = new Database(dbPath, {
		fileMustExist: true,
		readonly: true,
	});
	db.pragma("query_only = ON");
	return db;
}

export function withM8Database<T>(
	callback: (db: M8Database) => T,
	dbPath?: string,
): T {
	const db = openM8Database(dbPath);
	try {
		return callback(db);
	} finally {
		db.close();
	}
}
