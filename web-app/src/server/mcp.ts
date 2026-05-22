import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";

import { searchRequestSchema } from "#/lib/m8-schemas";
import {
	getM8StatsFromDefaultDb,
	retrieveM8FromDefaultDb,
} from "#/server/retrieval";

export function createM8McpServer(): McpServer {
	const server = new McpServer({
		name: "m8-agent",
		version: "1.0.0",
	});

	server.registerTool(
		"search_m8",
		{
			title: "Search Dirtywave M8 references",
			description:
				"Search the local Dirtywave M8 index across videos, official manual, Open M8 Tips, and The M8 Companion. Use this before answering factual Dirtywave M8 questions. Answer in the user's language, use only retrieved results for factual claims, and always include a final Sources section listing compact source labels with each result's citation_url. If official manual and community sources conflict, describe both explicitly. If results are weak or insufficient, say what is missing instead of guessing.",
			inputSchema: searchRequestSchema,
		},
		(input) => {
			const results = retrieveM8FromDefaultDb(input);
			return {
				content: [
					{
						type: "text",
						text: JSON.stringify({ results }, null, 2),
					},
				],
				structuredContent: { results },
			};
		},
	);

	server.registerTool(
		"get_m8_stats",
		{
			title: "Get M8 index stats",
			description: "Return counts for the local M8 SQLite index.",
		},
		() => {
			const stats = getM8StatsFromDefaultDb();
			return {
				content: [
					{
						type: "text",
						text: JSON.stringify({ stats }, null, 2),
					},
				],
				structuredContent: { stats },
			};
		},
	);

	return server;
}
