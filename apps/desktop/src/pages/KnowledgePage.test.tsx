// @vitest-environment jsdom
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { getLegacyKnowledgeOverview } from "../api/legacy";
import { getWikiHealth } from "../api/knowledge";
import { KnowledgePage } from "./KnowledgePage";

vi.mock("../api/legacy", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/legacy")>();
  return { ...original, getLegacyKnowledgeOverview: vi.fn() };
});

vi.mock("../api/knowledge", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/knowledge")>();
  return { ...original, getWikiHealth: vi.fn() };
});

beforeEach(() => {
  vi.mocked(getWikiHealth).mockResolvedValue({
    score: 95, page_count: 12, link_count: 18,
    issues: [{ code: "orphan_page", severity: "warning", knowledge_id: "k1", detail: "孤立页面" }],
  });
  vi.mocked(getLegacyKnowledgeOverview).mockResolvedValue({
    data_as_of: "2026-09-22T00:00:00Z",
    job_count: 1028,
    interview_count: 503,
    question_count: 4816,
    coding_count: 324,
    needs_review_count: 684,
    top_skills: [{ label: "Python", count: 318 }],
    top_companies: [{ label: "OpenAI", count: 124 }],
    top_locations: [{ label: "上海", count: 66 }],
    questions: [{
      record_id: "legacy_question_1",
      kind: "question",
      title: "如何设计可审计的 Agent 工作流？",
      topic: "Agent 工程",
      company: "示例科技",
      role: "AI 工程师",
      observed_at: "2026-09-18",
      review_status: "historical_unconfirmed",
      source_path: "data/统一数据/问题明细.csv",
      source_sha256: "a".repeat(64),
      row_number: 42,
    }],
    interviews: [],
  });
});

afterEach(cleanup);

it("默认展示真实历史统计、技能和可追溯面试题", async () => {
  render(<KnowledgePage />);

  expect(await screen.findByText("1,028")).toBeTruthy();
  expect(screen.getByText("4,816")).toBeTruthy();
  expect(screen.getByText("Python")).toBeTruthy();
  expect(screen.getByText("OpenAI")).toBeTruthy();
  expect(screen.getByText("如何设计可审计的 Agent 工作流？")).toBeTruthy();
  expect(screen.getByText(/问题明细\.csv · 第 42 行/)).toBeTruthy();
  expect(screen.getByText(/统计不等于个人事实/)).toBeTruthy();
  expect(await screen.findByText("Wiki 健康度 95")).toBeTruthy();
  expect(screen.getByText(/12 个页面 · 18 条链接/)).toBeTruthy();
});
