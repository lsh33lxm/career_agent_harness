import { MemoryRouter } from "react-router-dom";
// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { createOfferPreparationProposal, createRejectionPatternProposal, listApplications, listInterviews, listOutcomes } from "../api/history";
import type { ApplicationRead, OutcomeRead } from "../api/history";
import { HistoryPage } from "./HistoryPage";

vi.mock("../api/history", () => ({ listApplications: vi.fn(), listInterviews: vi.fn(), listOutcomes: vi.fn(), createOfferPreparationProposal: vi.fn(), createRejectionPatternProposal: vi.fn() }));
const application = (id: string): ApplicationRead => ({
  entity_id: id, revision: 4, opportunity_id: "opportunity_a", opportunity_revision: 2,
  state: "interview", resume_revision_id: "resume_revision_a", submission_authority: "user_confirmed",
  submission_evidence_ref_id: null, submitted_at: "2026-09-20T10:00:00",
});
const outcome = (id: string): OutcomeRead => ({
  entity_id: `outcome_${id}`, revision: 1, application_id: id, application_revision: 2,
  result: "rejection", occurred_at: "2026-09-21T12:00:00", authority: "portal_receipt",
  evidence_refs: ["evidence_1"], recorded_by: "user",
});
beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(listInterviews).mockResolvedValue([]);
  vi.mocked(createRejectionPatternProposal).mockResolvedValue({ proposal_id: "rejection_pattern_1" });
  vi.mocked(createOfferPreparationProposal).mockResolvedValue({ proposal_id: "offer_prep_1" });
});
afterEach(cleanup);

it("renders real current state separately from historical outcome revisions and evidence", async () => {
  vi.mocked(listApplications).mockResolvedValue([application("application_a")]);
  vi.mocked(listOutcomes).mockResolvedValue([outcome("application_a")]);
  render(<MemoryRouter><HistoryPage /></MemoryRouter>);
  expect(await screen.findByRole("heading", { name: "未通过" })).toBeTruthy();
  expect(screen.getByText("当前阶段：面试中")).toBeTruthy();
  expect(screen.getByText("application_a#2")).toBeTruthy();
  expect(screen.getByText("门户回执")).toBeTruthy();
  expect(screen.getByText("evidence_1")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "分析投递结果模式" }));
  expect(await screen.findByText(/投递结果分析已创建/)).toBeTruthy();
});

it("does not infer outcomes for empty applications", async () => {
  vi.mocked(listApplications).mockResolvedValue([]);
  render(<MemoryRouter><HistoryPage /></MemoryRouter>);
  expect(await screen.findByText("还没有申请记录")).toBeTruthy();
  expect(listOutcomes).not.toHaveBeenCalled();
});

it("reports failures and retries without substituting sample data", async () => {
  vi.mocked(listApplications).mockRejectedValueOnce(new Error("offline")).mockResolvedValue([application("application_a")]);
  vi.mocked(listOutcomes).mockRejectedValueOnce(new Error("offline")).mockResolvedValue([]);
  render(<MemoryRouter><HistoryPage /></MemoryRouter>);
  fireEvent.click(await screen.findByRole("button", { name: "重试申请" }));
  fireEvent.click(await screen.findByRole("button", { name: "重试结果" }));
  expect(await screen.findByText("这份申请尚无已记录的结果。")).toBeTruthy();
});

it("ignores a stale result when another application is selected", async () => {
  let finishFirst!: (value: OutcomeRead[]) => void;
  vi.mocked(listApplications).mockResolvedValue([application("application_a"), application("application_b")]);
  vi.mocked(listOutcomes).mockImplementation((id) => id === "application_a"
    ? new Promise((resolve) => { finishFirst = resolve; }) : Promise.resolve([]));
  render(<MemoryRouter><HistoryPage /></MemoryRouter>);
  fireEvent.change(await screen.findByLabelText("选择申请"), { target: { value: "application_b" } });
  expect(await screen.findByText("这份申请尚无已记录的结果。")).toBeTruthy();
  await act(async () => finishFirst([outcome("application_a")]));
  expect(screen.queryByText("outcome_application_a#1")).toBeNull();
});
