// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { getEvidence, listEvidence } from "./evidence";

afterEach(() => { vi.unstubAllGlobals(); delete window.__ACH_CONFIG__; });
it("requests bounded pages and exact references through authenticated local client", async () => {
  window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "synthetic-test-token" };
  const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({ items: [], next_cursor: null })));
  vi.stubGlobal("fetch", fetcher);
  await listEvidence("ref:a&b");
  expect(fetcher.mock.calls[0][0]).toBe("http://127.0.0.1:8765/api/v1/evidence?limit=25&after=ref%3Aa%26b");
  expect(fetcher.mock.calls[0][1].headers.get("Authorization")).toBe("Bearer synthetic-test-token");
  fetcher.mockResolvedValue(new Response(JSON.stringify({})));
  await getEvidence("ref:a/b");
  expect(fetcher.mock.calls[1][0]).toBe("http://127.0.0.1:8765/api/v1/evidence/ref%3Aa%2Fb");
});
