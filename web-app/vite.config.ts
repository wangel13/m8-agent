import babel from "@rolldown/plugin-babel";
import tailwindcss from "@tailwindcss/vite";
import { devtools } from "@tanstack/devtools-vite";
import { tanstackStart } from "@tanstack/react-start/plugin/vite";
import viteReact, { reactCompilerPreset } from "@vitejs/plugin-react";
import { nitro } from "nitro/vite";
import { defineConfig, loadEnv } from "vite";

const isTest = process.env.VITEST === "true";

const config = defineConfig(({ mode }) => {
	const buildEnv = loadEnv(mode, process.cwd(), "VITE_UMAMI_");
	const hasUmamiScriptUrl = Boolean(buildEnv.VITE_UMAMI_SCRIPT_URL);
	const hasUmamiWebsiteId = Boolean(buildEnv.VITE_UMAMI_WEBSITE_ID);

	if (hasUmamiScriptUrl !== hasUmamiWebsiteId) {
		throw new Error(
			"VITE_UMAMI_SCRIPT_URL and VITE_UMAMI_WEBSITE_ID must be set together",
		);
	}

	return {
		resolve: { tsconfigPaths: true },
		plugins: [
			!isTest && devtools(),
			nitro({ rollupConfig: { external: [/^@sentry\//] } }),
			tailwindcss(),
			tanstackStart(),
			viteReact(),
			babel({ presets: [reactCompilerPreset()] }),
		],
	};
});

export default config;
