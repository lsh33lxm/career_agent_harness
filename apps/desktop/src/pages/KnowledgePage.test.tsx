// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { getLegacyKnowledgeOverview } from "../api/legacy";
import { apiRequest } from "../api/client";
import {
  createKnowledgeProposal,
  getWikiHealth,
  getWikiRevisions,
  reviewKnowledgeProposal,
} from "../api/knowledge";
import { KnowledgePage } from "./KnowledgePage";

vi.mock("../api/legacy", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/legacy")>();
  return { ...original, getLegacyKnowledgeOverview: vi.fn() };
});

vi.mock("../api/knowledge", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/knowledge")>();
  return {
    ...original,
    createKnowledgeProposal: vi.fn(),
    getWikiHealth: vi.fn(),
    getWikiRevisions: vi.fn(),
    reviewKnowledgeProposal: vi.fn(),
  };
});

vi.mock("../api/client", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/client")>();
  return { ...original, apiRequest: vi.fn() };
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
  vi.mocked(apiRequest).mockImplementation(async (path) => {
    if (path === "/api/v1/source-connectors") return [];
    if (path === "/api/v1/knowledge/search") return {
      items: [{
        knowledge_id: "knowledge_1",
        revision: 2,
        title: "Agent 工作流",
        snippet: "可审计任务编排",
        score: 1,
        lexical_score: 1,
        semantic_score: 1,
        search_mode: "hybrid",
        category: "skill",
        status: "approved",
        citation: {
          knowledge_id: "knowledge_1",
          revision: 2,
          evidence_refs: ["evidence_1"],
          source_type: "document",
          source_locator: "local:test.md",
          authority: "document_supported",
        },
      }],
      query: "Agent",
      evidence_sufficient: true,
      message: null,
      next_cursor: null,
    };
    throw new Error(`unexpected request ${path}`);
  });
  vi.mocked(getWikiRevisions).mockResolvedValue([{
    knowledge_id: "knowledge_1",
    revision: 2,
    title: "Agent 工作流",
    content: "原始正文",
    evidence_refs: ["evidence_1"],
  }]);
  vi.mocked(createKnowledgeProposal).mockResolvedValue({
    proposal_id: "proposal_1",
    target_knowledge_id: "knowledge_1",
    base_revision: 2,
    category: "skill",
    title: "Agent 工作流（修订）",
    proposed_content: "修订正文",
    status: "pending",
  });
  vi.mocked(reviewKnowledgeProposal).mockResolvedValue({
    proposal_id: "proposal_1",
    target_knowledge_id: "knowledge_1",
    base_revision: 2,
    category: "skill",
    title: "Agent 工作流（修订）",
    proposed_content: "修订正文",
    status: "approved",
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

it("Wiki 编辑先创建提案，用户再次批准后才发布", async () => {
  render(<KnowledgePage />);
  fireEvent.change(screen.getByLabelText("检索知识"), { target: { value: "Agent" } });
  fireEvent.click(screen.getByRole("button", { name: "检索" }));
  expect(await screen.findByRole("heading", { name: "Agent 工作流" })).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "提出修订" }));
  expect(await screen.findByDisplayValue("原始正文")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("页面标题"), { target: { value: "Agent 工作流（修订）" } });
  fireEvent.change(screen.getByLabelText("页面正文"), { target: { value: "修订正文" } });
  fireEvent.click(screen.getByRole("button", { name: "保存为待确认修订" }));
  await waitFor(() => expect(createKnowledgeProposal).toHaveBeenCalled());
  expect(reviewKnowledgeProposal).not.toHaveBeenCalled();

  fireEvent.click(screen.getByRole("button", { name: "批准并发布" }));
  await waitFor(() => expect(reviewKnowledgeProposal).toHaveBeenCalledWith(
    "proposal_1",
    "approved",
    "用户确认桌面端 Wiki 修订",
  ));
  expect(screen.getByText("修订已批准并发布为新版本。")).toBeTruthy();
});
