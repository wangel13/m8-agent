type UmamiEventData = Record<string, boolean | number | string>;

declare global {
	interface Window {
		umami?: {
			track: (eventName: string, data?: UmamiEventData) => void;
		};
	}
}

export function trackUmamiEvent(
	eventName: string,
	data?: UmamiEventData,
): void {
	if (typeof window === "undefined") {
		return;
	}

	try {
		window.umami?.track(eventName, data);
	} catch {
		// Analytics must never block the action being tracked.
	}
}
