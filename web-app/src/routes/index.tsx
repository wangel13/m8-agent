import { useForm } from "@tanstack/react-form";
import { useMutation, useQuery } from "@tanstack/react-query";
import { createFileRoute } from "@tanstack/react-router";
import { Play, SearchIcon, SquareArrowOutUpRight } from "lucide-react";
import { useEffect, useState } from "react";

import { ModeToggle } from "#/components/mode-toggle";
import { Badge } from "#/components/ui/badge";
import { Button, buttonVariants } from "#/components/ui/button";
import {
	Card,
	CardAction,
	CardContent,
	CardDescription,
	CardHeader,
	CardTitle,
} from "#/components/ui/card";
import {
	Collapsible,
	CollapsibleContent,
	CollapsibleTrigger,
} from "#/components/ui/collapsible";
import { Input } from "#/components/ui/input";
import {
	InputGroup,
	InputGroupAddon,
	InputGroupButton,
	InputGroupInput,
} from "#/components/ui/input-group";
import {
	Item,
	ItemActions,
	ItemContent,
	ItemDescription,
	ItemFooter,
	ItemGroup,
	ItemTitle,
} from "#/components/ui/item";
import { Label } from "#/components/ui/label";
import {
	Select,
	SelectContent,
	SelectGroup,
	SelectItem,
	SelectTrigger,
	SelectValue,
} from "#/components/ui/select";
import type { M8Source, RetrievalResult, StatsResult } from "#/lib/m8-schemas";

export const Route = createFileRoute("/")({ component: Home });

const isPublicSearch = import.meta.env.VITE_PUBLIC_SEARCH === "true";

type SearchState = {
	query: string;
	source: M8Source;
	lang: string;
	limit: string;
};

type TokenState = {
	token: string;
};

const sourceOptions: Array<{ value: M8Source; label: string }> = [
	{ value: "all", label: "All sources" },
	{ value: "manual", label: "Manual" },
	{ value: "community_tips", label: "Open M8 Tips" },
	{ value: "companion", label: "M8 Companion" },
	{ value: "video", label: "Videos" },
];

const defaultTokenValues: TokenState = {
	token: "",
};

const defaultSearchValues: SearchState = {
	query: "USB audio options",
	source: "all",
	lang: "any",
	limit: "8",
};

function buildMcpClientConfig(origin: string) {
	return `{
  "mcpServers": {
    "m8-agent": {
      "url": "${origin}/mcp",
      "headers": {
        "Authorization": "Bearer <M8_AUTH_TOKEN>"
      }
    }
  }
}`;
}

function Home() {
	const [savedToken, setSavedToken] = useState("");
	const [siteOrigin, setSiteOrigin] = useState("http://localhost:3000");
	const [mcpConfigOpen, setMcpConfigOpen] = useState(false);

	const tokenForm = useForm({
		defaultValues: defaultTokenValues,
		onSubmit: ({ value }) => {
			window.localStorage.setItem("m8-auth-token", value.token);
			setSavedToken(value.token);
			searchMutation.reset();
		},
	});

	const searchForm = useForm({
		defaultValues: defaultSearchValues,
		onSubmit: ({ value }) => {
			searchMutation.mutate(value);
		},
	});

	const searchMutation = useMutation({
		mutationFn: (request: SearchState) => searchM8(savedToken, request),
	});

	useEffect(() => {
		const stored = window.localStorage.getItem("m8-auth-token") ?? "";
		tokenForm.setFieldValue("token", stored);
		setSavedToken(stored);
		setSiteOrigin(window.location.origin);
	}, [tokenForm]);

	const statsQuery = useQuery({
		queryKey: ["m8-stats", savedToken],
		queryFn: () => fetchStats(savedToken),
		enabled: isPublicSearch || savedToken.length > 0,
	});

	const stats = statsQuery.data?.stats ?? null;
	const results = searchMutation.data?.results ?? [];
	const error = errorMessage(statsQuery.error ?? searchMutation.error);
	const loading = searchMutation.isPending;
	const searchDisabled = (!isPublicSearch && !savedToken) || loading;
	const mcpClientConfig = buildMcpClientConfig(siteOrigin);

	return (
		<main className="mx-auto flex w-full max-w-5xl flex-col gap-6 px-4 py-8">
			<header className="flex flex-col gap-4">
				<div className="flex items-start justify-between gap-4">
					<div className="flex flex-col gap-2">
						<Badge variant="default" className="w-fit">
							M8 MCP
						</Badge>
						<h1 className="font-heading text-4xl font-semibold tracking-normal md:text-5xl">
							M8 Search
						</h1>
					</div>
					<ModeToggle />
				</div>
				{stats ? <StatsGrid stats={stats} /> : null}
			</header>

			<Card>
				<CardHeader>
					<CardTitle>
						{isPublicSearch ? "MCP server" : "Access token"}
					</CardTitle>
					<CardDescription>
						{isPublicSearch
							? "Search here without an LLM, or copy this config into an MCP-capable agent."
							: "Enter the server token to access search and stats."}
					</CardDescription>
				</CardHeader>
				{isPublicSearch ? (
					<CardContent>
						<Collapsible
							open={mcpConfigOpen}
							onOpenChange={setMcpConfigOpen}
							className="flex flex-col gap-3"
						>
							<div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
								<p className="text-sm text-muted-foreground">
									MCP endpoint:{" "}
									<code className="text-foreground">{siteOrigin}/mcp</code>
								</p>
								<CollapsibleTrigger
									render={<Button variant="outline" size="sm" />}
								>
									{mcpConfigOpen ? "Hide config" : "Show config"}
								</CollapsibleTrigger>
							</div>
							<CollapsibleContent>
								<pre className="overflow-x-auto rounded-md border bg-muted p-3 text-xs/relaxed text-muted-foreground">
									<code>{mcpClientConfig}</code>
								</pre>
							</CollapsibleContent>
						</Collapsible>
					</CardContent>
				) : (
					<CardContent>
						<form
							className="flex flex-col gap-3 md:flex-row md:items-end"
							onSubmit={(event) => {
								event.preventDefault();
								event.stopPropagation();
								void tokenForm.handleSubmit();
							}}
						>
							<tokenForm.Field name="token">
								{(field) => (
									<div className="flex flex-1 flex-col gap-2">
										<Label htmlFor={field.name}>Token</Label>
										<Input
											id={field.name}
											name={field.name}
											type="password"
											value={field.state.value}
											placeholder="M8_AUTH_TOKEN"
											onBlur={field.handleBlur}
											onChange={(event) =>
												field.handleChange(event.target.value)
											}
										/>
									</div>
								)}
							</tokenForm.Field>
							<Button type="submit" className="md:w-32">
								Unlock
							</Button>
						</form>
					</CardContent>
				)}
			</Card>

			<Card>
				<CardHeader>
					<CardTitle>Search index</CardTitle>
					<CardDescription>
						Search videos, the official manual, Open M8 Tips, and The M8
						Companion.
					</CardDescription>
				</CardHeader>
				<CardContent>
					<form
						className="flex flex-col gap-4"
						onSubmit={(event) => {
							event.preventDefault();
							event.stopPropagation();
							void searchForm.handleSubmit();
						}}
					>
						<searchForm.Field name="query">
							{(field) => (
								<div className="flex flex-col gap-2">
									<Label htmlFor={field.name}>Search</Label>
									<InputGroup>
										<InputGroupInput
											id={field.name}
											name={field.name}
											value={field.state.value}
											placeholder="table command modulation"
											onBlur={field.handleBlur}
											onKeyDown={(event) => {
												if (event.key === "Enter") {
													event.preventDefault();
													void searchForm.handleSubmit();
												}
											}}
											onChange={(event) =>
												field.handleChange(event.target.value)
											}
										/>
										<InputGroupAddon align="inline-end">
											<InputGroupButton
												type="button"
												variant="secondary"
												disabled={searchDisabled}
												onClick={() => {
													void searchForm.handleSubmit();
												}}
											>
												<SearchIcon data-icon="inline-start" />
												{loading ? "Searching" : "Search"}
											</InputGroupButton>
										</InputGroupAddon>
									</InputGroup>
								</div>
							)}
						</searchForm.Field>

						<div className="grid gap-3 md:grid-cols-[1fr_150px_120px]">
							<searchForm.Field name="source">
								{(field) => (
									<div className="flex flex-col gap-2">
										<Label>Source</Label>
										<Select
											value={field.state.value}
											onValueChange={(value) => {
												if (value) {
													field.handleChange(value as M8Source);
												}
											}}
										>
											<SelectTrigger className="w-full">
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												<SelectGroup>
													{sourceOptions.map((option) => (
														<SelectItem key={option.value} value={option.value}>
															{option.label}
														</SelectItem>
													))}
												</SelectGroup>
											</SelectContent>
										</Select>
									</div>
								)}
							</searchForm.Field>

							<searchForm.Field name="lang">
								{(field) => (
									<div className="flex flex-col gap-2">
										<Label>Language</Label>
										<Select
											value={field.state.value}
											onValueChange={(value) => {
												if (value) {
													field.handleChange(value);
												}
											}}
										>
											<SelectTrigger className="w-full">
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												<SelectGroup>
													<SelectItem value="any">Any</SelectItem>
													<SelectItem value="en">English</SelectItem>
													<SelectItem value="ru">Russian</SelectItem>
												</SelectGroup>
											</SelectContent>
										</Select>
									</div>
								)}
							</searchForm.Field>

							<searchForm.Field name="limit">
								{(field) => (
									<div className="flex flex-col gap-2">
										<Label>Limit</Label>
										<Select
											value={field.state.value}
											onValueChange={(value) => {
												if (value) {
													field.handleChange(value);
												}
											}}
										>
											<SelectTrigger className="w-full">
												<SelectValue />
											</SelectTrigger>
											<SelectContent>
												<SelectGroup>
													{["5", "8", "12", "20"].map((value) => (
														<SelectItem key={value} value={value}>
															{value}
														</SelectItem>
													))}
												</SelectGroup>
											</SelectContent>
										</Select>
									</div>
								)}
							</searchForm.Field>
						</div>
					</form>
				</CardContent>
			</Card>

			{error ? (
				<Card>
					<CardContent>
						<p className="text-sm text-destructive">{error}</p>
					</CardContent>
				</Card>
			) : null}

			<ItemGroup>
				{results.map((result) => (
					<ResultItem key={resultKey(result)} result={result} />
				))}
			</ItemGroup>
		</main>
	);
}

function StatsGrid({ stats }: { stats: StatsResult }) {
	return (
		<dl className="grid grid-cols-1 gap-3 text-sm md:grid-cols-3">
			<Stat label="Videos" value={stats.videos} />
			{/* <Stat label="Chunks" value={stats.transcript_chunks} /> */}
			<Stat label="Docs" value={stats.documents} />
			{/* <Stat label="Doc chunks" value={stats.document_chunks} /> */}
			<Card size="sm">
				<CardHeader>
					<CardAction>
						<a
							href="https://linktr.ee/ramen_ya"
							target="_blank"
							rel="noreferrer"
							className={buttonVariants({ size: "icon" })}
						>
							<Play data-icon="inline-start" />
						</a>
					</CardAction>
					<CardTitle>Like M8 Search?</CardTitle>
					<CardDescription>
						If this project was useful, you can check out my music on streaming
						platforms. Thank you!
					</CardDescription>
				</CardHeader>
			</Card>
		</dl>
	);
}

function ResultItem({ result }: { result: RetrievalResult }) {
	return (
		<Item variant="outline">
			<ItemContent>
				<ItemTitle className="text-sm font-heading">
					<a href={result.citation_url} target="_blank" rel="noreferrer">
						{result.title}
					</a>
				</ItemTitle>
				<ItemDescription className="line-clamp-none text-justify leading-7 text-xs/relaxed">
					{result.text}
				</ItemDescription>
			</ItemContent>
			<ItemActions>
				<a
					href={result.citation_url}
					target="_blank"
					rel="noreferrer"
					className={buttonVariants({ size: "icon" })}
				>
					<SquareArrowOutUpRight data-icon="inline-start" />
				</a>
			</ItemActions>
			<ItemFooter>
				<div className="flex flex-wrap items-center gap-2">
					<Badge variant="outline">{result.source_type}</Badge>
					<Badge variant="outline">{result.authority}</Badge>
					<Badge variant="default">{result.location}</Badge>
				</div>
			</ItemFooter>
		</Item>
	);
}

function Stat({ label, value }: { label: string; value: number }) {
	return (
		<Card size="sm">
			<CardHeader>
				<CardDescription>{label}</CardDescription>
				<CardTitle className="tabular-nums text-2xl">
					{value.toLocaleString()}
				</CardTitle>
			</CardHeader>
		</Card>
	);
}

async function fetchStats(token: string): Promise<{ stats: StatsResult }> {
	const response = await fetch("/api/stats", {
		headers: authHeaders(token),
	});

	if (!response.ok) {
		throw new Error(await responseText(response));
	}

	return response.json() as Promise<{ stats: StatsResult }>;
}

async function searchM8(
	token: string,
	request: SearchState,
): Promise<{ results: RetrievalResult[] }> {
	const response = await fetch("/api/search", {
		method: "POST",
		headers: {
			...authHeaders(token),
			"Content-Type": "application/json",
		},
		body: JSON.stringify({
			query: request.query,
			limit: Number(request.limit),
			sources: [request.source],
			lang: request.lang === "any" ? undefined : request.lang,
		}),
	});

	if (!response.ok) {
		throw new Error(await responseText(response));
	}

	return response.json() as Promise<{ results: RetrievalResult[] }>;
}

function authHeaders(token: string): HeadersInit {
	if (isPublicSearch) {
		return {};
	}
	return token ? { Authorization: `Bearer ${token}` } : {};
}

function errorMessage(error: unknown): string | null {
	if (!error) {
		return null;
	}
	return error instanceof Error ? error.message : String(error);
}

async function responseText(response: Response): Promise<string> {
	const text = await response.text();
	if (!text) {
		return `${response.status} ${response.statusText}`;
	}

	try {
		const data = JSON.parse(text) as { error?: string };
		return data.error ?? text;
	} catch {
		return text;
	}
}

function resultKey(result: RetrievalResult): string {
	return `${result.source_type}-${result.citation_url}-${result.location}-${result.text.slice(0, 32)}`;
}
