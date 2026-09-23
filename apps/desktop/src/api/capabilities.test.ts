// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import { getCapabilities } from "./capabilities";

describe("capability workspace client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.__ACH_CONFIG__ = undefined;
  });

  it("authenticates and encodes candidate and exact graph ids", async () => {
    window.__ACH_CONFIG__ = {
      apiBaseUrl: "http://127.0.0.1:43123",
      launchToken: "ephemeral-test-token",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ candidate_id: "candidate/one" }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await getCapabilities("candidate/one", "graph version/1");

    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(
      "http://127.0.0.1:43123/api/v1/capabilities/candidate%2Fone?graph_version_id=graph%20version%2F1",
    );
    expect(new Headers(request.headers).get("Authorization")).toBe(
      "Bearer ephemeral-test-token",
    );
  });
});
