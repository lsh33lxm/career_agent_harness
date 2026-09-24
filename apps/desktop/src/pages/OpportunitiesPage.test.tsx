// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getOpportunity,
  listOpportunities,
  setOpportunityUserPriority,
  type OpportunitySummary,
} from "../api/client";
import { OpportunitiesPage } from "./OpportunitiesPage";

vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return { ...original, getOpportunity: vi.fn(), listOpportunities: vi.fn(), setOpportunityUserPriority: vi.fn() };
});
vi.mock("./JobRadarPanel", () => ({
  JobRadarPanel: () => <section aria-label="历史岗位库">历史岗位入口</section>,
}));

function opportunity(level: "low" | "urgent" = "low"): OpportunitySummary {
  return {
    opportunity: {
      entity_id: "opportunity_001",
      revision: level === "urgent" ? 4 : 3,
      schema_version: 1,
      state: "qualified",
    },
    job: { job_id: "job_001", revision: 2 },
    suggested_priority: {
      opportunity_id: "opportunity_001",
      level: "high",
      reasons: ["与目标岗位方向一致"],
      input_revisions: [{ entity_id: "job_001", revision: 2 }],
      calculated_at: "2026-09-18T10:00:00Z",
      score: null,
      rank: null,
    },
    user_priority: {
      opportunity_id: "opportunity_001",
      level,
      actor: "user",
      set_at: "2026-09-18T10:01:00Z",
      reason: "由用户决定",
    },
  };
}

beforeEach(() => {
  vi.mocked(getOpportunity).mockReset();
  vi.mocked(listOpportunities).mockReset();
  vi.mocked(setOpportunityUserPriority).mockReset();
});
afterEach(cleanup);

describe("OpportunitiesPage", () => {
  it("用中文引导用户从历史岗位加入求职流程", async () => {
    vi.mocked(listOpportunities).mockResolvedValue([]);
    render(<OpportunitiesPage />);
    expect(await screen.findByRole("heading", { name: "还没有加入求职流程的岗位" })).toBeTruthy();
    expect(screen.getByText(/在上方历史岗位库中选择岗位/)).toBeTruthy();
    expect(screen.queryByText(/Job ID|Proposal ID|candidate_001/)).toBeNull();
  });

  it("区分系统建议和用户优先级，并只由用户保存修改", async () => {
    const initial = opportunity();
    const updated = opportunity("urgent");
    vi.mocked(listOpportunities).mockResolvedValue([initial]);
    vi.mocked(setOpportunityUserPriority).mockResolvedValue({
      entity_id: "opportunity_001",
      revision: 4,
      revision_id: "revision_004",
      event_id: "event_004",
    });
    vi.mocked(getOpportunity).mockResolvedValue(updated);

    render(<OpportunitiesPage />);
    const record = await screen.findByRole("article");
    expect(within(record).getByText("系统建议")).toBeTruthy();
    expect(within(record).getByText("与目标岗位方向一致")).toBeTruthy();
    fireEvent.change(within(record).getByRole("combobox"), { target: { value: "urgent" } });
    fireEvent.click(within(record).getByRole("button", { name: "保存" }));
    await waitFor(() => expect(setOpportunityUserPriority).toHaveBeenCalledWith(
      "opportunity_001",
      expect.objectContaining({ expected_revision: 3, level: "urgent" }),
      expect.stringMatching(/^user_priority_/),
    ));
    await waitFor(() => expect(record.querySelector(".priority-badge--urgent")?.textContent).toBe("紧急"));
    expect(record.querySelector(".priority-badge--high")?.textContent).toBe("高");
  });

  it("读取失败时显示中文错误并允许重试", async () => {
    vi.mocked(listOpportunities)
      .mockRejectedValueOnce(new Error("职业核心暂时不可用"))
      .mockResolvedValueOnce([]);
    render(<OpportunitiesPage />);
    expect((await screen.findByRole("alert")).textContent).toContain("职业核心暂时不可用");
    fireEvent.click(screen.getByRole("button", { name: "重试" }));
    expect(await screen.findByRole("heading", { name: "还没有加入求职流程的岗位" })).toBeTruthy();
  });
});
