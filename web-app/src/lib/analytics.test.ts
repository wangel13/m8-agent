// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from "vitest";
import { trackUmamiEvent } from "./analytics";

describe("trackUmamiEvent", () => {
	afterEach(() => {
		delete window.umami;
	});

	it("forwards event data to Umami", () => {
		const track = vi.fn();
		window.umami = { track };

		trackUmamiEvent("search", {
			source: "video",
			lang: "en",
			limit: 8,
			channel: "NearTao",
		});

		expect(track).toHaveBeenCalledOnce();
		expect(track).toHaveBeenCalledWith("search", {
			source: "video",
			lang: "en",
			limit: 8,
			channel: "NearTao",
		});
	});

	it("does not fail when the tracker is unavailable", () => {
		expect(() => trackUmamiEvent("show-config")).not.toThrow();
	});

	it("does not expose tracker failures to the application", () => {
		window.umami = {
			track: () => {
				throw new Error("blocked");
			},
		};

		expect(() => trackUmamiEvent("search")).not.toThrow();
	});
});
