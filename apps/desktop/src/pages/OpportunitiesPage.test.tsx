// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  admitOpportunityManually,
  admitOpportunityProposal,
  getOpportunity,
  listOpportunities,
  setOpportunityUserPriority,
  type OpportunitySummary,
} from "../api/client";
import { OpportunitiesPage } from "./OpportunitiesPage";

vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return {
    ...original,
    admitOpportunityManually: vi.fn(),
    admitOpportunityProposal: vi.fn(),
    getOpportunity: vi.fn(),
    listOpportunities: vi.fn(),
    setOpportunityUserPriority: vi.fn(),
  };
});

function opportunity(overrides: Partial<OpportunitySummary> = {}): OpportunitySummary {
  return {
    opportunity: {
      entity_id: "opportunity_001",
      revision: 3,
      schema_version: 1,
      state: "qualified",
    },
    job: { job_id: "job_001", revision: 2 },
    suggested_priority: {
      opportunity_id: "opportunity_001",
      level: "high",
      reasons: ["Target role alignment"],
      input_revisions: [{ entity_id: "job_001", revision: 2 }],
      calculated_at: "2026-09-18T10:00:00Z",
      score: null,
      rank: null,
    },
    user_priority: {
      opportunity_id: "opportunity_001",
      level: "low",
      actor: "user",
      set_at: "2026-09-18T10:01:00Z",
      reason: "Waiting for more evidence",
    },
    ...overrides,
  };
}

beforeEach(() => {
  vi.mocked(admitOpportunityManually).mockReset();
  vi.mocked(admitOpportunityProposal).mockReset();
  vi.mocked(getOpportunity).mockReset();
  vi.mocked(listOpportunities).mockReset();
  vi.mocked(setOpportunityUserPriority).mockReset();
});

afterEach(cleanup);

describe("OpportunitiesPage", () => {
  it("renders the empty state from a real empty response", async () => {
    vi.mocked(listOpportunities).mockResolvedValue([]);

    render(<OpportunitiesPage />);

    expect(await screen.findByRole("heading", { name: "No opportunities yet" })).toBeTruthy();
    expect(screen.getByText("0 items")).toBeTruthy();
  });

  it("renders canonical opportunity and separate priority values", async () => {
    vi.mocked(listOpportunities).mockResolvedValue([opportunity()]);

    render(<OpportunitiesPage />);

    const record = await screen.findByRole("article");
    expect(within(record).getByRole("heading", { name: "job_001" })).toBeTruthy();
    expect(within(record).getByText("opportunity_001")).toBeTruthy();
    expect(
      within(record).getByLabelText("Suggested priority for job_001").textContent,
    ).toContain("High");
    expect(within(record).getByLabelText("User priority for job_001").textContent).toContain(
      "Low",
    );
  });

  it("admits a manually selected job and reloads the list", async () => {
    vi.mocked(listOpportunities).mockResolvedValue([]);
    vi.mocked(admitOpportunityManually).mockResolvedValue({
      admission: { opportunity: null },
      commit: {
        entity_id: "opportunity_001",
        revision: 1,
        revision_id: "revision_001",
        event_id: "event_001",
      },
    });

    render(<OpportunitiesPage />);
    await screen.findByRole("heading", { name: "No opportunities yet" });
    fireEvent.click(screen.getByRole("button", { name: "Add opportunity" }));
    fireEvent.change(screen.getByLabelText("Job ID"), { target: { value: "job_001" } });
    fireEvent.change(screen.getByLabelText("Job revision"), { target: { value: "2" } });
    fireEvent.click(screen.getByRole("button", { name: "Add opportunity" }));

    await waitFor(() => expect(admitOpportunityManually).toHaveBeenCalledTimes(1));
    expect(admitOpportunityManually).toHaveBeenCalledWith(
      expect.objectContaining({ job_id: "job_001", job_revision: 2 }),
      expect.stringMatching(/^manual_admission_/),
    );
    const manualRequest = vi.mocked(admitOpportunityManually).mock.calls[0][0];
    expect("opportunity_id" in manualRequest).toBe(false);
    expect("decision_id" in manualRequest).toBe(false);
    expect(listOpportunities).toHaveBeenCalledTimes(2);
  });

  it("keeps a successful admission closed when the list refresh fails", async () => {
    vi.mocked(listOpportunities)
      .mockResolvedValueOnce([])
      .mockRejectedValueOnce(new Error("Refresh unavailable"))
      .mockResolvedValueOnce([opportunity()]);
    vi.mocked(admitOpportunityManually).mockResolvedValue({
      admission: { opportunity: null },
      commit: {
        entity_id: "opportunity_001",
        revision: 1,
        revision_id: "revision_001",
        event_id: "event_001",
      },
    });

    render(<OpportunitiesPage />);
    await screen.findByRole("heading", { name: "No opportunities yet" });
    fireEvent.click(screen.getByRole("button", { name: "Add opportunity" }));
    fireEvent.change(screen.getByLabelText("Job ID"), { target: { value: "job_001" } });
    fireEvent.click(screen.getByRole("button", { name: "Add opportunity" }));

    expect((await screen.findByRole("alert")).textContent).toContain("Refresh unavailable");
    expect(screen.queryByRole("heading", { name: "Opportunity admission" })).toBeNull();
    expect(admitOpportunityManually).toHaveBeenCalledTimes(1);

    fireEvent.click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("heading", { name: "job_001" })).toBeTruthy();
    expect(admitOpportunityManually).toHaveBeenCalledTimes(1);
  });

  it("confirms an agent proposal through the proposal admission endpoint", async () => {
    vi.mocked(listOpportunities).mockResolvedValue([]);
    vi.mocked(admitOpportunityProposal).mockResolvedValue({
      admission: { opportunity: null },
      commit: {
        entity_id: "opportunity_001",
        revision: 1,
        revision_id: "revision_001",
        event_id: "event_001",
      },
    });

    render(<OpportunitiesPage />);
    await screen.findByRole("heading", { name: "No opportunities yet" });
    fireEvent.click(screen.getByRole("button", { name: "Add opportunity" }));
    fireEvent.click(screen.getByRole("button", { name: "Confirm proposal" }));
    fireEvent.change(screen.getByLabelText("Job ID"), { target: { value: "job_001" } });
    fireEvent.change(screen.getByLabelText("Proposal ID"), {
      target: { value: "proposal_001" },
    });
    fireEvent.change(screen.getByLabelText("Proposal reason"), {
      target: { value: "Target role alignment" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Confirm and add" }));

    await waitFor(() => expect(admitOpportunityProposal).toHaveBeenCalledTimes(1));
    expect(admitOpportunityProposal).toHaveBeenCalledWith(
      expect.objectContaining({
        job_id: "job_001",
        proposal_id: "proposal_001",
        proposal_reason: "Target role alignment",
        proposed_by: "agent",
      }),
      expect.stringMatching(/^proposal_admission_/),
    );
    const proposalRequest = vi.mocked(admitOpportunityProposal).mock.calls[0][0];
    expect("opportunity_id" in proposalRequest).toBe(false);
    expect("decision_id" in proposalRequest).toBe(false);
  });

  it("updates user priority without changing the suggested projection", async () => {
    const initial = opportunity();
    const updated = opportunity({
      opportunity: { ...initial.opportunity, revision: 4 },
      user_priority: { ...initial.user_priority!, level: "urgent" },
    });
    vi.mocked(listOpportunities).mockResolvedValue([initial]);
    vi.mocked(setOpportunityUserPriority).mockResolvedValue({
      entity_id: "opportunity_001",
      revision: 4,
      revision_id: "revision_004",
      event_id: "event_004",
    });
    vi.mocked(getOpportunity).mockResolvedValue(updated);

    render(<OpportunitiesPage />);
    const select = await screen.findByRole("combobox", { name: "Set user priority for job_001" });
    fireEvent.change(select, { target: { value: "urgent" } });
    const userPriority = screen.getByLabelText("User priority for job_001");
    fireEvent.click(within(userPriority).getByRole("button", { name: "Save" }));

    await waitFor(() => expect(getOpportunity).toHaveBeenCalledWith("opportunity_001"));
    expect(screen.getByLabelText("Suggested priority for job_001").textContent).toContain("High");
    expect(screen.getByLabelText("User priority for job_001").textContent).toContain("Urgent");
    expect(setOpportunityUserPriority).toHaveBeenCalledWith(
      "opportunity_001",
      expect.objectContaining({ expected_revision: 3, level: "urgent" }),
      expect.stringMatching(/^user_priority_/),
    );
  });

  it("reports a saved priority separately when detail refresh fails", async () => {
    const initial = opportunity();
    const updated = opportunity({
      opportunity: { ...initial.opportunity, revision: 4 },
      user_priority: { ...initial.user_priority!, level: "urgent" },
    });
    vi.mocked(listOpportunities)
      .mockResolvedValueOnce([initial])
      .mockResolvedValueOnce([updated]);
    vi.mocked(setOpportunityUserPriority).mockResolvedValue({
      entity_id: "opportunity_001",
      revision: 4,
      revision_id: "revision_004",
      event_id: "event_004",
    });
    vi.mocked(getOpportunity).mockRejectedValue(new Error("Detail refresh unavailable"));

    render(<OpportunitiesPage />);
    const select = await screen.findByRole("combobox", { name: "Set user priority for job_001" });
    fireEvent.change(select, { target: { value: "urgent" } });
    const userPriority = screen.getByLabelText("User priority for job_001");
    fireEvent.click(within(userPriority).getByRole("button", { name: "Save" }));

    const refreshAlert = await screen.findByRole("alert");
    expect(refreshAlert.textContent).toContain(
      "Priority was saved, but refresh failed: Detail refresh unavailable",
    );
    expect(screen.getByLabelText("Suggested priority for job_001").textContent).toContain("High");
    expect(setOpportunityUserPriority).toHaveBeenCalledTimes(1);
    expect(within(userPriority).getByRole<HTMLButtonElement>("button", { name: "Save" }).disabled).toBe(
      true,
    );

    fireEvent.click(within(refreshAlert).getByRole("button", { name: "Reload" }));
    await waitFor(() =>
      expect(screen.getByLabelText("User priority for job_001").textContent).toContain("Urgent"),
    );
    expect(screen.getByLabelText("Suggested priority for job_001").textContent).toContain("High");
    expect(setOpportunityUserPriority).toHaveBeenCalledTimes(1);
    expect(listOpportunities).toHaveBeenCalledTimes(2);
  });

  it("shows an API error and retries the list request", async () => {
    vi.mocked(listOpportunities)
      .mockRejectedValueOnce(new Error("Core unavailable"))
      .mockResolvedValueOnce([opportunity()]);

    render(<OpportunitiesPage />);

    expect((await screen.findByRole("alert")).textContent).toContain("Core unavailable");
    fireEvent.click(screen.getByRole("button", { name: "Retry" }));

    expect(await screen.findByRole("heading", { name: "job_001" })).toBeTruthy();
    expect(listOpportunities).toHaveBeenCalledTimes(2);
  });
});
