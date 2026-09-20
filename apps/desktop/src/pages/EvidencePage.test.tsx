import { MemoryRouter } from "react-router-dom";
// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { ApiError } from "../api/client";
import { getEvidence, listEvidence } from "../api/evidence";
import type { EvidenceProvenance } from "../api/evidence";
import { EvidencePage } from "./EvidencePage";

vi.mock("../api/evidence", () => ({ listEvidence: vi.fn(), getEvidence: vi.fn() }));
const evidence = (id = "ref_a"): EvidenceProvenance => ({
  evidence_ref: { evidence_ref_id: id, snapshot_id: "snapshot_a", artifact_id: "artifact_a", selector: "archive-index:exact-digest" },
  snapshot: { snapshot_id: "snapshot_a", source_id: "source_a", captured_at: "2026-09-21T00:00:00Z", artifact_id: "artifact_a" },
  source: { source_id: "source_a", source_type: "legacy_historical_unconfirmed", locator: "file:///historical-origin" },
  artifact: { artifact_id: "artifact_a", sha256: "a".repeat(64), media_type: "text/plain", artifact_class: "sensitive", byte_length: 1234 },
});
beforeEach(() => vi.resetAllMocks());
afterEach(cleanup);

it("keeps loading and empty states explicit", async () => {
  let complete!: (data: { items: []; next_cursor: null }) => void;
  vi.mocked(listEvidence).mockReturnValue(new Promise((resolve) => { complete = resolve; }));
  render(<MemoryRouter><EvidencePage /></MemoryRouter>);
  expect(screen.getByRole("status").textContent).toContain("正在读取");
  await act(async () => complete({ items: [], next_cursor: null }));
  expect(await screen.findByText("还没有证据记录。")).toBeTruthy();
  expect(getEvidence).not.toHaveBeenCalled();
});

it("retries failures without substituting mock evidence", async () => {
  vi.mocked(listEvidence).mockRejectedValueOnce(new Error("offline")).mockResolvedValue({ items: [], next_cursor: null });
  render(<MemoryRouter><EvidencePage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "重试列表" }));
  expect(await screen.findByText("还没有证据记录。")).toBeTruthy();
});

it("shows exact metadata and historical unconfirmed boundary, keeping locator inert", async () => {
  vi.mocked(listEvidence).mockResolvedValue({ items: [evidence()], next_cursor: null });
  vi.mocked(getEvidence).mockResolvedValue(evidence());
  render(<MemoryRouter><EvidencePage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: /ref_a/ }));
  expect(await screen.findByText("a".repeat(64))).toBeTruthy();
  expect(screen.getByText(/保存材料不代表确认/)).toBeTruthy();
  const locator = screen.getByText("file:///historical-origin");
  expect(locator.tagName).toBe("DD");
  expect(screen.queryByRole("link", { name: "file:///historical-origin" })).toBeNull();
});

it("handles missing detail and retry", async () => {
  vi.mocked(listEvidence).mockResolvedValue({ items: [evidence()], next_cursor: null });
  vi.mocked(getEvidence).mockRejectedValueOnce(new ApiError("not found", 404)).mockResolvedValue(evidence());
  render(<MemoryRouter><EvidencePage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: /ref_a/ }));
  expect(await screen.findByText("这条证据引用不存在。")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "重试详情" }));
  expect(await screen.findByText("a".repeat(64))).toBeTruthy();
});

it("uses the server cursor and clears detail between pages", async () => {
  vi.mocked(listEvidence).mockResolvedValueOnce({ items: [evidence()], next_cursor: "ref_a" })
    .mockResolvedValueOnce({ items: [evidence("ref_b")], next_cursor: null });
  vi.mocked(getEvidence).mockResolvedValue(evidence());
  render(<MemoryRouter><EvidencePage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: /ref_a/ }));
  expect(await screen.findByText("a".repeat(64))).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "下一页" }));
  expect(await screen.findByRole("button", { name: /ref_b/ })).toBeTruthy();
  expect(listEvidence).toHaveBeenLastCalledWith("ref_a", expect.any(AbortSignal));
  expect(screen.queryByLabelText("证据详情")).toBeNull();
  expect(screen.queryByRole("button", { name: "下一页" })).toBeNull();
  expect(screen.getByText("本页 1 条记录")).toBeTruthy();
});
