import { createFileRoute } from "@tanstack/react-router";

import {
	jsonResponse,
	preflightResponse,
	requireSearchAccess,
} from "#/server/http";
import { getYoutubeChannelsFromDefaultDb } from "#/server/retrieval";

export const Route = createFileRoute("/api/channels")({
	server: {
		handlers: {
			GET: async ({ request }) => {
				const accessError = requireSearchAccess(request);
				if (accessError) {
					return accessError;
				}

				return jsonResponse(getYoutubeChannelsFromDefaultDb());
			},
			OPTIONS: async () => preflightResponse(),
		},
	},
});
