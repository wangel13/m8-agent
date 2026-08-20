import { TanStackDevtools } from "@tanstack/react-devtools";
import type { QueryClient } from "@tanstack/react-query";
import {
	createRootRouteWithContext,
	HeadContent,
	Scripts,
} from "@tanstack/react-router";
import { TanStackRouterDevtoolsPanel } from "@tanstack/react-router-devtools";
import { ThemeProvider } from "#/components/theme-provider";
import { env } from "#/env";
import TanStackQueryDevtools from "../integrations/tanstack-query/devtools";
import TanstackQueryProvider from "../integrations/tanstack-query/root-provider";
import appCss from "../styles.css?url";

const siteUrl = env.VITE_SITE_URL?.replace(/\/$/, "") ?? "";
const siteTitle = "M8 Search";
const siteDescription =
	"Search M8 Tracker videos, the official manual, Open M8 Tips, and The M8 Companion from one focused MCP-ready index.";
const socialImage = siteUrl ? `${siteUrl}/og-image.png` : "/og-image.png";

interface MyRouterContext {
	queryClient: QueryClient;
}

export const Route = createRootRouteWithContext<MyRouterContext>()({
	head: () => ({
		meta: [
			{
				charSet: "utf-8",
			},
			{
				name: "viewport",
				content: "width=device-width, initial-scale=1",
			},
			{
				title: siteTitle,
			},
			{
				name: "description",
				content: siteDescription,
			},
			{
				name: "keywords",
				content:
					"M8 Tracker, Dirtywave M8, M8 search, MCP server, tracker music, music production, M8 manual",
			},
			{
				name: "robots",
				content: "index, follow",
			},
			{
				name: "application-name",
				content: siteTitle,
			},
			{
				name: "apple-mobile-web-app-title",
				content: siteTitle,
			},
			{
				name: "theme-color",
				content: "#101828",
			},
			{
				name: "color-scheme",
				content: "light dark",
			},
			{
				property: "og:title",
				content: siteTitle,
			},
			{
				property: "og:description",
				content: siteDescription,
			},
			{
				property: "og:type",
				content: "website",
			},
			{
				property: "og:site_name",
				content: siteTitle,
			},
			{
				property: "og:image",
				content: socialImage,
			},
			{
				property: "og:image:width",
				content: "1200",
			},
			{
				property: "og:image:height",
				content: "630",
			},
			{
				property: "og:image:alt",
				content: "M8 Search preview card",
			},
			{
				name: "twitter:card",
				content: "summary_large_image",
			},
			{
				name: "twitter:title",
				content: siteTitle,
			},
			{
				name: "twitter:description",
				content: siteDescription,
			},
			{
				name: "twitter:image",
				content: socialImage,
			},
			{
				name: "twitter:image:alt",
				content: "M8 Search preview card",
			},
		],
		links: [
			{
				rel: "stylesheet",
				href: appCss,
			},
			{
				rel: "icon",
				href: "/favicon.ico",
				sizes: "any",
			},
			{
				rel: "icon",
				href: "/favicon.svg",
				type: "image/svg+xml",
			},
			{
				rel: "apple-touch-icon",
				href: "/logo192.png",
			},
			{
				rel: "manifest",
				href: "/manifest.json",
			},
			...(siteUrl
				? [
						{
							rel: "canonical",
							href: siteUrl,
						},
					]
				: []),
		],
		scripts:
			env.VITE_UMAMI_SCRIPT_URL && env.VITE_UMAMI_WEBSITE_ID
				? [
						{
							defer: true,
							src: env.VITE_UMAMI_SCRIPT_URL,
							"data-website-id": env.VITE_UMAMI_WEBSITE_ID,
						},
					]
				: [],
	}),
	shellComponent: RootDocument,
});

function RootDocument({ children }: { children: React.ReactNode }) {
	const { queryClient } = Route.useRouteContext();

	return (
		<html
			className="scrollbar-gutter-stable"
			lang="en"
			suppressHydrationWarning
		>
			<head>
				<HeadContent />
			</head>
			<body>
				<ThemeProvider defaultTheme="system" storageKey="theme">
					<TanstackQueryProvider queryClient={queryClient}>
						{children}
						<TanStackDevtools
							config={{
								position: "bottom-right",
							}}
							plugins={[
								{
									name: "Tanstack Router",
									render: <TanStackRouterDevtoolsPanel />,
								},
								TanStackQueryDevtools,
							]}
						/>
					</TanstackQueryProvider>
				</ThemeProvider>
				<Scripts />
			</body>
		</html>
	);
}
