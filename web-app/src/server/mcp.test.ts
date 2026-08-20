import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { expect, it } from "vitest";

import { createM8McpServer } from "#/server/mcp";

it("publishes YouTube channel discovery and filtering through MCP", async () => {
	const server = createM8McpServer();
	const client = new Client({ name: "m8-agent-test", version: "1.0.0" });
	const [clientTransport, serverTransport] =
		InMemoryTransport.createLinkedPair();

	await server.connect(serverTransport);
	await client.connect(clientTransport);

	try {
		const result = await client.listTools();
		const toolNames = result.tools.map((tool) => tool.name);
		const searchTool = result.tools.find((tool) => tool.name === "search_m8");

		expect(toolNames).toContain("list_youtube_channels");
		expect(searchTool?.inputSchema).toMatchObject({
			properties: {
				channel: { type: "string" },
			},
		});
	} finally {
		await client.close();
		await server.close();
	}
});
