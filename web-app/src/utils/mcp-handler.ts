import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { WebStandardStreamableHTTPServerTransport } from "@modelcontextprotocol/sdk/server/webStandardStreamableHttp.js";

import {
	corsHeaders,
	preflightResponse,
	requireBearerAuth,
} from "#/server/http";

export async function handleMcpRequest(
	request: Request,
	createServer: () => McpServer,
): Promise<Response> {
	if (request.method === "OPTIONS") {
		return preflightResponse();
	}

	const authError = requireBearerAuth(request);
	if (authError) {
		return authError;
	}

	const server = createServer();
	const transport = new WebStandardStreamableHTTPServerTransport({
		enableJsonResponse: true,
		sessionIdGenerator: undefined,
	});

	try {
		await server.connect(transport);
		const response = await transport.handleRequest(request);
		return withCors(response);
	} catch (error) {
		console.error("MCP handler error:", error);
		return Response.json(
			{
				jsonrpc: "2.0",
				error: {
					code: -32603,
					message: "Internal server error",
					data: error instanceof Error ? error.message : String(error),
				},
				id: null,
			},
			{ status: 500, headers: corsHeaders() },
		);
	} finally {
		await server.close();
	}
}

function withCors(response: Response): Response {
	const headers = new Headers(response.headers);
	for (const [key, value] of Object.entries(corsHeaders())) {
		headers.set(key, value);
	}

	return new Response(response.body, {
		status: response.status,
		statusText: response.statusText,
		headers,
	});
}
