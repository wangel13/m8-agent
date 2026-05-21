import { z } from "zod";

export const sourceSchema = z.enum([
	"all",
	"video",
	"manual",
	"community_tips",
	"companion",
]);

export const searchRequestSchema = z.object({
	query: z.string().trim().min(1),
	limit: z.coerce.number().int().min(1).max(50).default(8),
	sources: z.array(sourceSchema).min(1).default(["all"]),
	lang: z.string().trim().min(1).optional(),
});

export type M8Source = z.infer<typeof sourceSchema>;
export type SearchRequest = z.infer<typeof searchRequestSchema>;

export type RetrievalResult = {
	source_type: Exclude<M8Source, "all">;
	authority: "official" | "community" | string;
	title: string;
	location: string;
	citation_url: string;
	text: string;
	score: number;
};

export type StatsResult = {
	videos: number;
	transcript_chunks: number;
	documents: number;
	document_chunks: number;
	document_chunks_by_source: Array<{
		source_type: string;
		chunks: number;
	}>;
};
