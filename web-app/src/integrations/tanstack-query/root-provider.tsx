import {
	QueryClient,
	QueryClientProvider,
	type QueryClientProviderProps,
} from "@tanstack/react-query";

export function getContext() {
	const queryClient = new QueryClient();

	return {
		queryClient,
	};
}
export default function TanstackQueryProvider({
	children,
	queryClient,
}: {
	children: QueryClientProviderProps["children"];
	queryClient: QueryClient;
}) {
	return (
		<QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
	);
}
