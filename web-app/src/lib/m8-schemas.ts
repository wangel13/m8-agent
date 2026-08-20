import { z } from "zod";

export const sourceSchema = z.enum([
	"all",
	"video",
	"manual",
	"community_tips",
	"companion",
]);

export const searchRequestSchema = z
	.object({
		query: z.string().trim().min(1),
		limit: z.coerce.number().int().min(1).max(50).default(8),
		sources: z.array(sourceSchema).min(1).optional(),
		lang: z.string().trim().min(1).optional(),
		channel: z.string().trim().min(1).optional(),
	})
	.superRefine((request, context) => {
		if (
			request.channel &&
			request.sources &&
			(request.sources.length !== 1 || request.sources[0] !== "video")
		) {
			context.addIssue({
				code: "custom",
				path: ["sources"],
				message:
					'When channel is set, sources must be omitted or exactly ["video"].',
			});
		}
	});

export type M8Source = z.infer<typeof sourceSchema>;
export type SearchRequest = z.infer<typeof searchRequestSchema>;

export type RetrievalResult = {
	source_type: Exclude<M8Source, "all">;
	authority: "official" | "community" | string;
	channel?: string;
	title: string;
	location: string;
	citation_url: string;
	text: string;
	score: number;
};

export type YoutubeChannel = {
	name: string;
	videos: number;
};

export type YoutubeChannelsResult = {
	channels: YoutubeChannel[];
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
