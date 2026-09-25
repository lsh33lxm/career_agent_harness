// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { advanceApplicationState, listApplications, listInterviews } from "../api/history";
import { downloadInterviewCalendar } from "../api/calendar";
import { ApplicationsPage } from "./ApplicationsPage";

vi.mock("../api/history", () => ({ listApplications: vi.fn(), listInterviews: vi.fn(), advanceApplicationState: vi.fn() }));
vi.mock("../api/calendar", () => ({ downloadInterviewCalendar: vi.fn() }));

describe("ApplicationsPage", () => {
  afterEach(() => cleanup());

  it("groups applications and sorts scheduled interviews", async () => {
    vi.mocked(listApplications).mockResolvedValue([
      { entity_id: "app_1", revision: 1, opportunity_id: "opp_1", opportunity_revision: 1, state: "interview", resume_revision_id: "resume_rev_1", submission_authority: "user_confirmed", submission_evidence_ref_id: null, submitted_at: null },
      { entity_id: "app_2", revision: 2, opportunity_id: "opp_2", opportunity_revision: 1, state: "preparing", resume_revision_id: null, submission_authority: null, submission_evidence_ref_id: null, submitted_at: null },
    ]);
    vi.mocked(listInterviews).mockImplementation(async (id) => id === "app_1" ? [
      { entity_id: "interview_late", revision: 1, application_id: id, application_revision: 1, round: "technical", scheduled_at: "2026-10-02T09:00:00+08:00", status: "scheduled", evidence_refs: [] },
      { entity_id: "interview_early", revision: 1, application_id: id, application_revision: 1, round: "screen", scheduled_at: "2026-10-01T09:00:00+08:00", status: "scheduled", evidence_refs: [] },
    ] : []);

    render(<ApplicationsPage />);
    expect(await screen.findByText("app_1")).toBeTruthy();
    expect(screen.getByLabelText("面试中").textContent).toContain("app_1");
    await waitFor(() => expect(screen.getByText(/2026年10月1日/)).toBeTruthy());
    expect(screen.getByLabelText("已安排面试").textContent?.indexOf("2026年10月1日")).toBeLessThan(screen.getByLabelText("已安排面试").textContent?.indexOf("2026年10月2日") ?? 0);
    fireEvent.click(screen.getByRole("button", { name: "月视图" }));
    expect(screen.getByLabelText("面试月视图")).toBeTruthy();
  });

  it("exports the current interview records as an ICS calendar", async () => {
    vi.mocked(listApplications).mockResolvedValue([{ entity_id: "app_1", revision: 1, opportunity_id: "opp_1", opportunity_revision: 1, state: "interview", resume_revision_id: null, submission_authority: null, submission_evidence_ref_id: null, submitted_at: null }]);
    vi.mocked(listInterviews).mockResolvedValue([{ entity_id: "interview_1", revision: 2, application_id: "app_1", application_revision: 1, round: "technical", scheduled_at: "2026-10-02T09:00:00+08:00", status: "scheduled", evidence_refs: [] }]);
    render(<ApplicationsPage />);
    const button = await screen.findByRole("button", { name: "导出 .ics" });
    button.click();
    expect(downloadInterviewCalendar).toHaveBeenCalledWith(expect.arrayContaining([expect.objectContaining({ entity_id: "interview_1" })]));
  });

  it("moves a post-submission card through the Career Core state API", async () => {
    const application = { entity_id: "app_drag", revision: 2, opportunity_id: "opp_1", opportunity_revision: 1, state: "submitted_by_user" as const, resume_revision_id: "resume_1", submission_authority: "user_confirmed" as const, submission_evidence_ref_id: null, submitted_at: "2026-10-01T09:00:00Z" };
    vi.mocked(listApplications).mockResolvedValue([application]);
    vi.mocked(listInterviews).mockResolvedValue([]);
    vi.mocked(advanceApplicationState).mockResolvedValue({ ...application, revision: 3, state: "screen" });
    render(<ApplicationsPage />);
    const card = await screen.findByText("app_drag");
    const target = screen.getByLabelText("筛选中");
    const dataTransfer = { setData: vi.fn(), getData: vi.fn(() => "app_drag") };
    fireEvent.dragStart(card.closest("article")!, { dataTransfer });
    fireEvent.drop(target, { dataTransfer });
    await waitFor(() => expect(advanceApplicationState).toHaveBeenCalledWith("app_drag", expect.objectContaining({ state: "screen", expected_revision: 2 })));
    expect(await screen.findByText(/已将申请移到/)).toBeTruthy();
  });
});
