// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { getCapabilityInboxItem, listCapabilityInbox, reviewCapabilityCandidate } from "./capabilityInbox";

afterEach(() => { vi.unstubAllGlobals(); window.__ACH_CONFIG__ = undefined; });
it("uses authenticated encoded paths and preserves the exact review body/key", async () => {
  window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:43123", launchToken: "inbox-test-token" };
  const fetchMock = vi.fn().mockImplementation(async () => new Response("{}", { status: 200 }));
  vi.stubGlobal("fetch", fetchMock);
  await listCapabilityInbox();
  await getCapabilityInboxItem("candidate/one");
  const body = { command_id: "command_001", expected_revision: 7, decision: "reject" as const, reason: "Exact reason" };
  await reviewCapabilityCandidate("candidate/one", body, "same-key");
  expect(fetchMock.mock.calls[0][0]).toBe("http://127.0.0.1:43123/api/v1/capability-inbox");
  expect(fetchMock.mock.calls[1][0]).toContain("candidate%2Fone");
  const [url, request] = fetchMock.mock.calls[2] as [string, RequestInit];
  expect(url).toContain("candidate%2Fone/review");
  expect(request.method).toBe("POST");
  expect(JSON.parse(request.body as string)).toEqual(body);
  expect(new Headers(request.headers).get("Authorization")).toBe("Bearer inbox-test-token");
  expect(new Headers(request.headers).get("X-Idempotency-Key")).toBe("same-key");
});
