// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { CommunicationMailboxPage } from "./CommunicationMailboxPage";

const mocks = vi.hoisted(() => ({ list: vi.fn(), summary: vi.fn(), accounts: vi.fn(), review: vi.fn(), transition: vi.fn() }));
vi.mock("../api/communications", () => ({
  listCommunicationDrafts: mocks.list,
  getCommunicationSummary: mocks.summary,
  listMailboxAccounts: mocks.accounts,
  reviewCommunicationDraft: mocks.review,
  transitionCommunicationDraft: mocks.transition,
}));

describe("CommunicationMailboxPage", () => {
  beforeEach(() => {
    mocks.list.mockResolvedValue([{ draft_id: "draft_1", opportunity_id: "opp_1", source_staging_id: null, channel: "email", recipient: "recruiter@example.test", body: "您好", status: "pending_review", provenance: {}, reviewed_by: null, review_reason: null }]);
    mocks.summary.mockResolvedValue({ daily_limit: 10, created_today: 1, remaining_today: 9, counts: { pending_review: 1 }, channel_counts: { email: 1 }, reply_count: 0, follow_up_count: 0 });
    mocks.accounts.mockResolvedValue([]);
    mocks.review.mockResolvedValue({});
    mocks.transition.mockResolvedValue({});
  });

  it("requires a reason and reviews one draft without sending", async () => {
    render(<CommunicationMailboxPage />);
    await screen.findByText("draft_1");
    const approve = screen.getByRole("button", { name: "批准" });
    expect((approve as HTMLButtonElement).disabled).toBe(true);
    fireEvent.change(screen.getByLabelText("审核理由 draft_1"), { target: { value: "我已核对收件人和正文" } });
    fireEvent.click(approve);
    await waitFor(() => expect(mocks.review).toHaveBeenCalledWith("draft_1", "approved", "我已核对收件人和正文"));
    expect(mocks.transition).not.toHaveBeenCalled();
  });
});
