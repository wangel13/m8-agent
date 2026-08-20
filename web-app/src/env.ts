import { createEnv } from "@t3-oss/env-core";
import { z } from "zod";

export const env = createEnv({
	server: {
		M8_AUTH_TOKEN: z.string().min(1).optional(),
		M8_CORS_ORIGIN: z.string().url().optional(),
		M8_DB_PATH: z.string().min(1).optional(),
		M8_PUBLIC_SEARCH: z.enum(["true", "false"]).optional(),
		SERVER_URL: z.string().url().optional(),
	},

	/**
	 * The prefix that client-side variables must have. This is enforced both at
	 * a type-level and at runtime.
	 */
	clientPrefix: "VITE_",

	client: {
		VITE_APP_TITLE: z.string().min(1).optional(),
		VITE_PUBLIC_SEARCH: z.enum(["true", "false"]).optional(),
		VITE_SITE_URL: z.string().url().optional(),
		VITE_UMAMI_SCRIPT_URL: z.string().url().optional(),
		VITE_UMAMI_WEBSITE_ID: z.string().uuid().optional(),
	},

	createFinalSchema: (shape) =>
		z.object(shape).superRefine((values, context) => {
			const hasScriptUrl = Boolean(values.VITE_UMAMI_SCRIPT_URL);
			const hasWebsiteId = Boolean(values.VITE_UMAMI_WEBSITE_ID);

			if (hasScriptUrl !== hasWebsiteId) {
				context.addIssue({
					code: "custom",
					message:
						"VITE_UMAMI_SCRIPT_URL and VITE_UMAMI_WEBSITE_ID must be set together",
					path: [
						hasScriptUrl ? "VITE_UMAMI_WEBSITE_ID" : "VITE_UMAMI_SCRIPT_URL",
					],
				});
			}
		}),

	/**
	 * What object holds the environment variables at runtime. This is usually
	 * `process.env` or `import.meta.env`.
	 */
	runtimeEnv: import.meta.env,

	/**
	 * By default, this library will feed the environment variables directly to
	 * the Zod validator.
	 *
	 * This means that if you have an empty string for a value that is supposed
	 * to be a number (e.g. `PORT=` in a ".env" file), Zod will incorrectly flag
	 * it as a type mismatch violation. Additionally, if you have an empty string
	 * for a value that is supposed to be a string with a default value (e.g.
	 * `DOMAIN=` in an ".env" file), the default value will never be applied.
	 *
	 * In order to solve these issues, we recommend that all new projects
	 * explicitly specify this option as true.
	 */
	emptyStringAsUndefined: true,
});
