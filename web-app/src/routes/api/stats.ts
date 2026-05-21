import { createFileRoute } from "@tanstack/react-router";

import {
	jsonResponse,
	preflightResponse,
	requireSearchAccess,
} from "#/server/http";
import { getM8StatsFromDefaultDb } from "#/server/retrieval";

export const Route = createFileRoute("/api/stats")({
	server: {
		handlers: {
			GET: async ({ request }) => {
				const accessError = requireSearchAccess(request);
				if (accessError) {
					return accessError;
				}

				return jsonResponse({ stats: getM8StatsFromDefaultDb() });
			},
			OPTIONS: async () => preflightResponse(),
		},
	},
});
