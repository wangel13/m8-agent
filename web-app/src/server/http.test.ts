import { afterEach, describe, expect, it } from "vitest";

import { requireBearerAuth, requireSearchAccess } from "#/server/http";

describe("HTTP auth", () => {
	const originalToken = process.env.M8_AUTH_TOKEN;
	const originalPublicSearch = process.env.M8_PUBLIC_SEARCH;

	afterEach(() => {
		process.env.M8_AUTH_TOKEN = originalToken;
		process.env.M8_PUBLIC_SEARCH = originalPublicSearch;
	});

	it("rejects requests when the token is missing", async () => {
		process.env.M8_AUTH_TOKEN = "secret";

		const response = requireBearerAuth(
			new Request("http://localhost/api/search"),
		);

		expect(response?.status).toBe(401);
	});

	it("accepts bearer token requests", () => {
		process.env.M8_AUTH_TOKEN = "secret";

		const response = requireBearerAuth(
			new Request("http://localhost/api/search", {
				headers: { Authorization: "Bearer secret" },
			}),
		);

		expect(response).toBeNull();
	});

	it("allows public search without bearer token", () => {
		process.env.M8_AUTH_TOKEN = "secret";
		process.env.M8_PUBLIC_SEARCH = "true";

		const response = requireSearchAccess(
			new Request("http://localhost/api/search"),
		);

		expect(response).toBeNull();
	});
});
