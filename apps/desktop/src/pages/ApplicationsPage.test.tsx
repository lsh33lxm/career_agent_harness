// @vitest-environment jsdom
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { listApplications, listInterviews } from "../api/history";
import { ApplicationsPage } from "./ApplicationsPage";

vi.mock("../api/history", () => ({ listApplications: vi.fn(), listInterviews: vi.fn() }));

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
  });
});
