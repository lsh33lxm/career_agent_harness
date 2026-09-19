// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { getToday, type TodayItem, type TodayQueue } from "../api/today";
import { useHealth } from "../api/useHealth";
import { TodayPage } from "./TodayPage";

vi.mock("../api/today", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/today")>();
  return { ...original, getToday: vi.fn() };
});

vi.mock("../api/useHealth", () => ({
  useHealth: vi.fn(),
}));

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

    expect(await screen.findByText(/今日队列为空/)).toBeTruthy();
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
  });
});
