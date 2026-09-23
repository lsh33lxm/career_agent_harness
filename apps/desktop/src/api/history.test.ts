// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { listApplications, listOutcomes } from "./history";

afterEach(() => { vi.unstubAllGlobals(); delete window.__ACH_CONFIG__; });
it("uses authenticated read-only requests and encodes the application id", async () => {
  window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "test-only" };
  const fetch = vi.fn().mockImplementation(async () => new Response("[]", { status: 200 }));
  vi.stubGlobal("fetch", fetch);
  await listApplications();
  await listOutcomes("application/a");
  expect(fetch.mock.calls[0][0]).toBe("http://127.0.0.1:8765/api/v1/applications");
  expect(fetch.mock.calls[1][0]).toBe("http://127.0.0.1:8765/api/v1/applications/application%2Fa/outcomes");
  expect(fetch.mock.calls[1][1].headers.get("Authorization")).toBe("Bearer test-only");
  expect(fetch.mock.calls[1][1].method).toBeUndefined();
  expect(fetch.mock.calls[1][1].body).toBeUndefined();
});
