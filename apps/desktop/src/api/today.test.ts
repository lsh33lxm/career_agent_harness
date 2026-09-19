// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import { getToday } from "./today";

describe("today API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.__ACH_CONFIG__ = undefined;
  });

  it("sends bearer authentication to the today read endpoint", async () => {
    window.__ACH_CONFIG__ = {
      apiBaseUrl: "http://127.0.0.1:43123",
      launchToken: "ephemeral-test-token",
    };
    const queue = {
      items: [],
      input_revisions: [],
      generated_at: "2026-09-20T08:00:00Z",
      policy_version: "today-policy-v1",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(queue), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getToday()).resolves.toEqual(queue);

    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://127.0.0.1:43123/api/v1/today");
    expect(new Headers(request.headers).get("Authorization")).toBe(
      "Bearer ephemeral-test-token",
    );
  });

  it("surfaces API errors without exposing the token", async () => {
    window.__ACH_CONFIG__ = {
      apiBaseUrl: "http://127.0.0.1:8765",
      launchToken: "secret-not-for-errors",
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 500 })));

    const error = await getToday().catch((reason: unknown) => reason);
    expect(String(error)).toContain("500");
    expect(String(error)).not.toContain("secret-not-for-errors");
  });
});
