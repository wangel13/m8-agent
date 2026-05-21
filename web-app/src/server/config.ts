import { resolve } from "node:path";

function readEnv(name: string): string | undefined {
	const value = process.env[name] ?? import.meta.env[name];
	return value && value.length > 0 ? value : undefined;
}

export function getDatabasePath(): string {
	return (
		readEnv("M8_DB_PATH") ??
		resolve(process.cwd(), "..", "data", "m8agent.sqlite")
	);
}

export function getAuthToken(): string | undefined {
	return readEnv("M8_AUTH_TOKEN");
}

export function isPublicSearchEnabled(): boolean {
	return readEnv("M8_PUBLIC_SEARCH") === "true";
}

export function getCorsOrigin(): string | undefined {
	return readEnv("M8_CORS_ORIGIN");
}
