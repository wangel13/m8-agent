import {
	getAuthToken,
	getCorsOrigin,
	isPublicSearchEnabled,
} from "#/server/config";

export function jsonResponse(data: unknown, init: ResponseInit = {}): Response {
	return new Response(JSON.stringify(data), {
		...init,
		headers: {
			"Content-Type": "application/json",
			...corsHeaders(),
			...init.headers,
		},
	});
}

export function preflightResponse(): Response {
	return new Response(null, {
		status: 204,
		headers: corsHeaders(),
	});
}

export function requireBearerAuth(request: Request): Response | null {
	const token = getAuthToken();
	if (!token) {
		return jsonResponse(
			{ error: "M8_AUTH_TOKEN is not configured on the server." },
			{ status: 500 },
		);
	}

	const expected = `Bearer ${token}`;
	if (request.headers.get("authorization") !== expected) {
		return jsonResponse({ error: "Unauthorized" }, { status: 401 });
	}

	return null;
}

export function requireSearchAccess(request: Request): Response | null {
	if (isPublicSearchEnabled()) {
		return null;
	}
	return requireBearerAuth(request);
}

export function corsHeaders(): HeadersInit {
	const origin = getCorsOrigin();
	if (!origin) {
		return {};
	}

	return {
		"Access-Control-Allow-Headers":
			"Authorization, Content-Type, Mcp-Session-Id",
		"Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
		"Access-Control-Allow-Origin": origin,
		Vary: "Origin",
	};
}
