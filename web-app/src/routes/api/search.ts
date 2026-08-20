import { createFileRoute } from "@tanstack/react-router";
import { ZodError } from "zod";

import { searchRequestSchema } from "#/lib/m8-schemas";
import {
	jsonResponse,
	preflightResponse,
	requireSearchAccess,
} from "#/server/http";
import {
	retrieveM8FromDefaultDb,
	UnknownYoutubeChannelError,
} from "#/server/retrieval";

export const Route = createFileRoute("/api/search")({
	server: {
		handlers: {
			OPTIONS: async () => preflightResponse(),
			POST: async ({ request }) => {
				const accessError = requireSearchAccess(request);
				if (accessError) {
					return accessError;
				}

				try {
					const input = searchRequestSchema.parse(await request.json());
					return jsonResponse({ results: retrieveM8FromDefaultDb(input) });
				} catch (error) {
					if (error instanceof ZodError) {
						return jsonResponse(
							{
								error: error.issues[0]?.message ?? "Invalid search request",
								issues: error.issues,
							},
							{ status: 400 },
						);
					}
					if (error instanceof UnknownYoutubeChannelError) {
						return jsonResponse({ error: error.message }, { status: 400 });
					}
					throw error;
				}
			},
		},
	},
});
