// @vitest-environment jsdom
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ApiError,
  admitOpportunityManually,
  getHealth,
  listOpportunities,
  setOpportunityUserPriority,
} from "./client";

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
    const [, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(fetchMock.mock.calls[0][0]).toBe("http://127.0.0.1:43123/health");
    expect(new Headers(request.headers).get("Authorization")).toBe(
      "Bearer ephemeral-test-token",
    );
  });

  it("rejects a non-loopback API address", async () => {
    window.__ACH_CONFIG__ = {
      apiBaseUrl: "http://0.0.0.0:8765",
      launchToken: "ephemeral-test-token",
    };

    await expect(getHealth()).rejects.toThrow("127.0.0.1");
  });

  it("rejects a hostname that only starts with the loopback text", async () => {
    window.__ACH_CONFIG__ = {
      apiBaseUrl: "http://127.0.0.1:8765@evil.test",
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

  it("sends bearer authentication for opportunity reads", async () => {
    window.__ACH_CONFIG__ = {
      apiBaseUrl: "http://127.0.0.1:8765",
      launchToken: "ephemeral-test-token",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify([]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(listOpportunities()).resolves.toEqual([]);

    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe("http://127.0.0.1:8765/api/v1/opportunities");
    expect(new Headers(request.headers).get("Authorization")).toBe(
      "Bearer ephemeral-test-token",
    );
  });

  it("sends bearer and idempotency headers for opportunity mutations", async () => {
    window.__ACH_CONFIG__ = {
      apiBaseUrl: "http://127.0.0.1:8765",
      launchToken: "ephemeral-test-token",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          admission: { opportunity: null },
          commit: {
            entity_id: "opportunity_001",
            revision: 1,
            revision_id: "revision_001",
            event_id: "event_001",
          },
        }),
        { status: 201, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await admitOpportunityManually(
      {
        command_id: "command_001",
        opportunity_id: "opportunity_001",
        decision_id: "decision_001",
        job_id: "job_001",
        job_revision: 1,
      },
      "manual-admission-001",
    );

    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    const headers = new Headers(request.headers);
    expect(url).toBe("http://127.0.0.1:8765/api/v1/opportunities/manual-admissions");
    expect(request.method).toBe("POST");
    expect(headers.get("Authorization")).toBe("Bearer ephemeral-test-token");
    expect(headers.get("X-Idempotency-Key")).toBe("manual-admission-001");
    expect(headers.get("Content-Type")).toBe("application/json");
  });

  it("encodes the target id and sends idempotency for priority changes", async () => {
    window.__ACH_CONFIG__ = {
      apiBaseUrl: "http://127.0.0.1:8765",
      launchToken: "ephemeral-test-token",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          entity_id: "opportunity_001",
          revision: 2,
          revision_id: "revision_002",
          event_id: "event_002",
        }),
        { status: 200, headers: { "Content-Type": "application/json" } },
      ),
    );
    vi.stubGlobal("fetch", fetchMock);

    await setOpportunityUserPriority(
      "opportunity_001",
      { command_id: "command_002", expected_revision: 1, level: "high" },
      "user-priority-001",
    );

    const [url, request] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toBe(
      "http://127.0.0.1:8765/api/v1/opportunities/opportunity_001/user-priority",
    );
    expect(request.method).toBe("PATCH");
    expect(new Headers(request.headers).get("X-Idempotency-Key")).toBe(
      "user-priority-001",
    );
  });
});
