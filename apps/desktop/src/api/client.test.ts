// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, getHealth } from "./client";

describe("local API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.__ACH_CONFIG__ = undefined;
  });

  it("sends the ephemeral token to the localhost health endpoint", async () => {
    window.__ACH_CONFIG__ = {
      apiBaseUrl: "http://127.0.0.1:43123",
      launchToken: "ephemeral-test-token",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          status: "ok",
          service: "agent-career-harness",
          version: "0.1.0",
          environment: "test",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getHealth()).resolves.toMatchObject({ status: "ok", version: "0.1.0" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://127.0.0.1:43123/health",
      expect.objectContaining({
        headers: { Authorization: "Bearer ephemeral-test-token" },
      }),
    );
  });

  it("rejects a non-loopback API address", async () => {
    window.__ACH_CONFIG__ = {
      apiBaseUrl: "http://0.0.0.0:8765",
      launchToken: "ephemeral-test-token",
    };

    await expect(getHealth()).rejects.toThrow("127.0.0.1");
  });

  it("surfaces authentication failures without exposing the token", async () => {
    window.__ACH_CONFIG__ = {
      apiBaseUrl: "http://127.0.0.1:8765",
      launchToken: "secret-not-for-errors",
    };
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 401 })));

    const error = await getHealth().catch((reason: unknown) => reason);
    expect(error).toBeInstanceOf(ApiError);
    expect(String(error)).not.toContain("secret-not-for-errors");
  });
});
