import { createFileRoute } from "@tanstack/react-router";

import { createM8McpServer } from "#/server/mcp";
import { handleMcpRequest } from "#/utils/mcp-handler";

export const Route = createFileRoute("/mcp")({
	server: {
		handlers: {
			DELETE: async ({ request }) =>
				handleMcpRequest(request, createM8McpServer),
			GET: async ({ request }) => handleMcpRequest(request, createM8McpServer),
			OPTIONS: async ({ request }) =>
				handleMcpRequest(request, createM8McpServer),
			POST: async ({ request }) => handleMcpRequest(request, createM8McpServer),
		},
	},
});
