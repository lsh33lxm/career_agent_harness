// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, it, vi } from "vitest";
import { EvidencePage } from "./EvidencePage";
import { HistoryPage } from "./HistoryPage";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); delete window.__ACH_CONFIG__; });

it("navigates History and Evidence without losing injected runtime authentication", async () => {
  const config = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "navigation-test-token" };
  window.__ACH_CONFIG__ = config;
  const fetcher = vi.fn(async (input: string) => new Response(JSON.stringify(
    input.includes("/evidence") ? { items: [], next_cursor: null } : [],
  )));
  vi.stubGlobal("fetch", fetcher);
  render(<MemoryRouter initialEntries={["/history"]}><Routes>
    <Route path="/history" element={<HistoryPage />} />
    <Route path="/history/evidence" element={<EvidencePage />} />
  </Routes></MemoryRouter>);
  expect(await screen.findByText("还没有申请记录")).toBeTruthy();
  fireEvent.click(screen.getByRole("link", { name: "查看证据来源" }));
  expect(await screen.findByRole("heading", { name: "证据来源" })).toBeTruthy();
  expect(await screen.findByText("还没有证据记录。")).toBeTruthy();
  expect(window.__ACH_CONFIG__).toBe(config);
  fireEvent.click(screen.getByRole("link", { name: "返回职业历程" }));
  expect(await screen.findByRole("heading", { name: "职业历程" })).toBeTruthy();
  expect(await screen.findByText("还没有申请记录")).toBeTruthy();
  expect(window.__ACH_CONFIG__).toBe(config);
  expect(fetcher).toHaveBeenCalledTimes(3);
  for (const call of vi.mocked(fetch).mock.calls) {
    expect(new Headers(call[1]?.headers).get("Authorization")).toBe("Bearer navigation-test-token");
  }
});
