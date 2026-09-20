// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { ApiError } from "../api/client";
import { listCapabilityInbox, reviewCapabilityCandidate, type InboxItem, type InboxReceipt } from "../api/capabilityInbox";
import { CapabilityInboxPage } from "./CapabilityInboxPage";

vi.mock("../api/capabilityInbox", () => ({ listCapabilityInbox: vi.fn(), reviewCapabilityCandidate: vi.fn() }));
const item: InboxItem = { revision: 7, candidate: {
  candidate_node_id: "candidate_node_001", proposed_canonical_name: "Candidate Alpha",
  proposed_description: "<script>unsafe()</script>", proposed_layer: "track",
  source_evidence_refs: ["evidence_001"], discovered_by: "agent:scout", status: "pending",
  reviewed_by: null, reviewed_by_kind: null, review_reason: null, merge_target_capability_id: null,
} };
const receipt: InboxReceipt = { candidate: { ...item.candidate, status: "accepted" },
  capability_id: "capability_new", graph_version: { graph_version_id: "graph_new" },
  commit: { entity_id: "candidate_node_001", revision: 8, revision_id: "revision_new", event_id: "event_new" },
};
beforeEach(() => { vi.mocked(listCapabilityInbox).mockReset().mockResolvedValue([item]); vi.mocked(reviewCapabilityCandidate).mockReset(); });
afterEach(cleanup);
async function choose() {
  await screen.findByText("Candidate Alpha");
  fireEvent.change(screen.getByLabelText("审核决定"), { target: { value: "accept" } });
  fireEvent.change(screen.getByLabelText("审核理由"), { target: { value: "Reviewed evidence" } });
}

it("handles loading, error retry and empty state", async () => {
  vi.mocked(listCapabilityInbox).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce([]);
  render(<MemoryRouter><CapabilityInboxPage /></MemoryRouter>);
  expect(screen.getByText("正在加载收件箱…")).toBeTruthy();
  fireEvent.click(await screen.findByRole("button", { name: "重试读取" }));
  expect(await screen.findByText("暂无能力候选")).toBeTruthy();
});

it("requires explicit reason and decision, renders safe provenance and disables in flight", async () => {
  let resolve!: (value: InboxReceipt) => void;
  vi.mocked(reviewCapabilityCandidate).mockImplementation(() => new Promise((done) => { resolve = done; }));
  render(<MemoryRouter><CapabilityInboxPage /></MemoryRouter>);
  await screen.findByText("Candidate Alpha");
  expect((screen.getByRole("button", { name: "确认审核" }) as HTMLButtonElement).disabled).toBe(true);
  expect(screen.getByText(/evidence_001/)).toBeTruthy();
  expect(document.querySelector("script")).toBeNull();
  await choose();
  fireEvent.click(screen.getByRole("button", { name: "确认审核" }));
  expect((screen.getByLabelText("审核理由") as HTMLTextAreaElement).disabled).toBe(true);
  vi.mocked(listCapabilityInbox).mockResolvedValue([{ candidate: receipt.candidate, revision: 8 }]);
  resolve(receipt);
  expect(await screen.findByText("审核已成功")).toBeTruthy();
  expect(await screen.findByText("图谱 ID：graph_new")).toBeTruthy();
  expect(screen.getByText("能力 ID：capability_new")).toBeTruthy();
  expect(screen.getByText("审核历史")).toBeTruthy();
  expect(reviewCapabilityCandidate).toHaveBeenCalledWith("candidate_node_001", expect.objectContaining({ expected_revision: 7, decision: "accept", reason: "Reviewed evidence" }), expect.any(String));
});

it("retains exact operation after response loss and replaces it for changed intent", async () => {
  vi.mocked(reviewCapabilityCandidate).mockRejectedValue(new ApiError("offline"));
  render(<MemoryRouter><CapabilityInboxPage /></MemoryRouter>);
  await choose();
  fireEvent.click(screen.getByRole("button", { name: "确认审核" }));
  fireEvent.click(await screen.findByRole("button", { name: "重试原审核" }));
  await waitFor(() => expect(reviewCapabilityCandidate).toHaveBeenCalledTimes(2));
  expect(vi.mocked(reviewCapabilityCandidate).mock.calls[1]).toEqual(vi.mocked(reviewCapabilityCandidate).mock.calls[0]);
  await screen.findByRole("button", { name: "重试原审核" });
  fireEvent.change(screen.getByLabelText("审核理由"), { target: { value: "Changed" } });
  fireEvent.click(screen.getByRole("button", { name: "确认审核" }));
  await waitFor(() => expect(reviewCapabilityCandidate).toHaveBeenCalledTimes(3));
  expect(vi.mocked(reviewCapabilityCandidate).mock.calls[2][2]).not.toBe(vi.mocked(reviewCapabilityCandidate).mock.calls[0][2]);
});

it("requires refresh and another decision after conflict without auto resubmit", async () => {
  vi.mocked(reviewCapabilityCandidate).mockRejectedValue(new ApiError("conflict", 409));
  render(<MemoryRouter><CapabilityInboxPage /></MemoryRouter>); await choose();
  fireEvent.click(screen.getByRole("button", { name: "确认审核" }));
  fireEvent.click(await screen.findByRole("button", { name: "刷新审核状态" }));
  await waitFor(() => expect((screen.getByLabelText("审核决定") as HTMLSelectElement).value).toBe(""));
  expect(reviewCapabilityCandidate).toHaveBeenCalledTimes(1);
});

it("keeps confirmed receipt when post-success read fails", async () => {
  vi.mocked(reviewCapabilityCandidate).mockResolvedValue(receipt);
  vi.mocked(listCapabilityInbox).mockResolvedValueOnce([item]).mockRejectedValue(new Error("offline"));
  render(<MemoryRouter><CapabilityInboxPage /></MemoryRouter>); await choose();
  fireEvent.click(screen.getByRole("button", { name: "确认审核" }));
  expect(await screen.findByText("审核已成功")).toBeTruthy();
  expect(await screen.findByText(/读取审核列表失败/)).toBeTruthy();
  expect(screen.queryByRole("button", { name: "重试原审核" })).toBeNull();
  expect((screen.getByRole("button", { name: "确认审核" }) as HTMLButtonElement).disabled).toBe(true);
});

it("disables self review and exposes reviewed history", async () => {
  vi.mocked(listCapabilityInbox).mockResolvedValue([{ ...item, candidate: { ...item.candidate, discovered_by: "user" } }]);
  render(<MemoryRouter><CapabilityInboxPage /></MemoryRouter>); await screen.findByText("Candidate Alpha");
  expect((screen.getByLabelText("审核决定") as HTMLSelectElement).disabled).toBe(true);
  expect(screen.getByText(/不能由同一用户审核/)).toBeTruthy();
  expect(reviewCapabilityCandidate).not.toHaveBeenCalled();
});

it("submits an explicit ignore decision and keeps conflict locked on failed refresh", async () => {
  vi.mocked(reviewCapabilityCandidate).mockRejectedValue(new ApiError("conflict", 409));
  vi.mocked(listCapabilityInbox).mockResolvedValueOnce([item]).mockRejectedValue(new Error("offline"));
  render(<MemoryRouter><CapabilityInboxPage /></MemoryRouter>); await choose();
  fireEvent.change(screen.getByLabelText("审核决定"), { target: { value: "reject" } });
  fireEvent.click(screen.getByRole("button", { name: "确认审核" }));
  fireEvent.click(await screen.findByRole("button", { name: "刷新审核状态" }));
  await screen.findByText(/读取审核列表失败/);
  expect((screen.getByLabelText("审核决定") as HTMLSelectElement).disabled).toBe(true);
  expect(reviewCapabilityCandidate).toHaveBeenCalledTimes(1);
  expect(vi.mocked(reviewCapabilityCandidate).mock.calls[0][1].decision).toBe("reject");
});
