import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";

import { createM8McpServer } from "#/server/mcp";

const server = createM8McpServer();
const transport = new StdioServerTransport();

await server.connect(transport);
