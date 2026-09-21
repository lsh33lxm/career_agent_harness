// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getToday, type TodayItem, type TodayQueue } from "../api/today";
import { getLegacyKnowledgeOverview } from "../api/legacy";
import { useHealth } from "../api/useHealth";
import { TodayPage } from "./TodayPage";

vi.mock("../api/today", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/today")>();
  return { ...original, getToday: vi.fn() };
});

vi.mock("../api/useHealth", () => ({
  useHealth: vi.fn(),
}));

vi.mock("../api/legacy", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/legacy")>();
  return { ...original, getLegacyKnowledgeOverview: vi.fn() };
});

function todayItem(overrides: Partial<TodayItem> = {}): TodayItem {
  return {
    item_id: "today:opportunity_action:opportunity_001",
    kind: "opportunity_action",
    source_refs: [{ entity_id: "opportunity_001", kind: "opportunity", revision: 3 }],
    reasons: [{ code: "user_priority_high", explanation: "用户将其标为高优先级。" }],
    user_priority: "high",
    suggested_priority: "urgent",
    deadline_at: "2026-09-22T10:00:00Z",
    interview_at: null,
    ...overrides,
  };
}

function todayQueue(items: TodayItem[] = []): TodayQueue {
  return {
    items,
    input_revisions: items.map((item) => item.source_refs[0]),
    generated_at: "2026-09-20T08:00:00Z",
    policy_version: "today-policy-v1",
  };
}

beforeEach(() => {
  vi.mocked(getToday).mockReset();
  vi.mocked(useHealth).mockReturnValue([
    {
      status: "online",
      data: { status: "ok", service: "agent-career-harness", version: "0.1.0", environment: "test" },
    },
    vi.fn(),
  ]);
  vi.mocked(getLegacyKnowledgeOverview).mockResolvedValue({
    data_as_of: null,
    job_count: 0,
    interview_count: 0,
    question_count: 0,
    coding_count: 0,
    needs_review_count: 0,
    top_skills: [],
    top_companies: [],
    top_locations: [],
    questions: [],
    interviews: [],
  });
});

afterEach(cleanup);

describe("TodayPage", () => {
  it("renders the Core queue items with their reasons and priorities", async () => {
    vi.mocked(getToday).mockResolvedValue(todayQueue([todayItem()]));

    render(<TodayPage />);

    const card = await screen.findByRole("article");
    expect(within(card).getByRole("heading", { name: "机会行动" })).toBeTruthy();
    expect(within(card).getByText("用户将其标为高优先级。")).toBeTruthy();
    expect(within(card).getByText("系统建议 紧急")).toBeTruthy();
    expect(within(card).getByText("用户优先级 高")).toBeTruthy();
    expect(within(card).getByText("2026-09-22 10:00")).toBeTruthy();
    expect(screen.getByText(/数据时点 2026-09-20 08:00/)).toBeTruthy();
  });

  it("renders an explicit empty state for an empty Core queue", async () => {
    vi.mocked(getToday).mockResolvedValue(todayQueue([]));

    render(<TodayPage />);

    expect(await screen.findByText("今日队列为空。先在“机会”导入或选择岗位，建立下一步行动。")).toBeTruthy();
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("有历史岗位但没有 Core 队列时给出可执行入口且不自动晋升岗位", async () => {
    vi.mocked(getToday).mockResolvedValue(todayQueue([]));
    vi.mocked(getLegacyKnowledgeOverview).mockResolvedValue({
      data_as_of: "2026-09-22T00:00:00Z",
      job_count: 1028,
      interview_count: 503,
      question_count: 4816,
      coding_count: 324,
      needs_review_count: 684,
      top_skills: [],
      top_companies: [],
      top_locations: [],
      questions: [],
      interviews: [],
    });

    render(<TodayPage />);

    expect(await screen.findByText("已有 1028 条历史岗位")).toBeTruthy();
    expect(screen.getByText(/历史岗位不会自动进入求职流程/)).toBeTruthy();
    expect(screen.getByRole("link", { name: "前往机会选择岗位" }).getAttribute("href")).toBe("/opportunities");
    expect(screen.queryByRole("article")).toBeNull();
  });

  it("shows an explicit unavailable state on API error and retries", async () => {
    vi.mocked(getToday)
      .mockRejectedValueOnce(new Error("Local API is unavailable"))
      .mockResolvedValueOnce(todayQueue([todayItem()]));

    render(<TodayPage />);

    const alert = await screen.findByRole("alert");
    expect(alert.textContent).toContain("Core 暂不可用");
    expect(screen.queryByRole("article")).toBeNull();

    fireEvent.click(within(alert).getByRole("button", { name: "重试" }));
    expect(await screen.findByRole("article")).toBeTruthy();
    expect(getToday).toHaveBeenCalledTimes(2);
  });

  it("renders items in the exact Core order without re-ranking", async () => {
    // Deliberately not in contract order: low priority first, urgent second.
    const lowFirst = todayItem({
      item_id: "today:opportunity_action:opportunity_low",
      user_priority: "low",
      reasons: [{ code: "user_priority_low", explanation: "低优先级事项。" }],
    });
    const urgentSecond = todayItem({
      item_id: "today:interview_prep:interview_urgent",
      kind: "interview_prep",
      source_refs: [{ entity_id: "interview_urgent", kind: "interview", revision: 1 }],
      user_priority: "urgent",
      reasons: [{ code: "interview_upcoming", explanation: "面试即将开始。" }],
    });
    vi.mocked(getToday).mockResolvedValue(todayQueue([lowFirst, urgentSecond]));

    render(<TodayPage />);

    const cards = await screen.findAllByRole("article");
    const ids = cards.map((card) => card.textContent ?? "");
    expect(ids[0]).toContain("today:opportunity_action:opportunity_low");
    expect(ids[1]).toContain("today:interview_prep:interview_urgent");
    const focus = screen.getByRole("region", { name: "今日焦点" });
    expect(focus.textContent).toContain(lowFirst.item_id);
    expect(focus.textContent).not.toContain(urgentSecond.item_id);
    expect(focus.textContent).toContain("沿用今日队列首项，不另行排序");
  });

  it("retains six honest regions and disables unavailable capture controls", async () => {
    const review = todayItem({ item_id: "review_only", kind: "review_request" });
    vi.mocked(getToday).mockResolvedValue(todayQueue([todayItem(), review]));
    render(<TodayPage />);
    await screen.findAllByRole("article");
    expect(screen.getByRole("heading", { name: "今天" })).toBeTruthy();
    for (const name of ["今日焦点", "今日队列", "需要你确认", "快速收集", "本周回看"]) {
      expect(screen.getByRole("region", { name: new RegExp(name) })).toBeTruthy();
    }
    const confirmation = screen.getByRole("region", { name: "需要你确认" });
    expect(confirmation.textContent).toContain("review_only");
    expect(confirmation.textContent).not.toContain("opportunity_001");
    const capture = screen.getByRole("region", { name: "快速收集" });
    expect(within(capture).getAllByRole("button").every((button) => (button as HTMLButtonElement).disabled)).toBe(true);
    expect(screen.getByText("周度回看尚未接入，当前不展示进度或完成数量。")).toBeTruthy();
  });
});
