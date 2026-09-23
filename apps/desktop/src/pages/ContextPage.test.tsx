// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  createMemoryProposal, deleteMemory, listMemories, listMemoryProposals,
  reviewMemoryProposal,
} from "../api/memory";
import { ContextPage } from "./ContextPage";

vi.mock("../api/memory", () => ({
  createMemoryProposal: vi.fn(), deleteMemory: vi.fn(), listMemories: vi.fn(),
  listMemoryProposals: vi.fn(), reviewMemoryProposal: vi.fn(),
}));

beforeEach(() => {
  vi.mocked(listMemories).mockResolvedValue([{
    relevance: 1,
    memory: {
      memory_id: "memory_1", revision: 1, memory_type: "preference",
      scope_kind: "user", scope_id: "local-user", status: "confirmed",
      content: "偏好本地优先的工具", source_type: "manual",
      source_locator: "manual://context", source_refs: [], confidence: 1,
      created_by: "USER", confirmed_by: "user", created_at: "2026-09-22T00:00:00Z",
    },
  }]);
  vi.mocked(listMemoryProposals).mockResolvedValue([{
    proposal_id: "memory_proposal_1", memory_type: "interest",
    content: "关注 Agent 工程岗位", source_locator: "manual://context",
    confidence: 1, created_by: "USER", status: "pending",
  }]);
  vi.mocked(createMemoryProposal).mockResolvedValue({} as never);
  vi.mocked(reviewMemoryProposal).mockResolvedValue({} as never);
  vi.mocked(deleteMemory).mockResolvedValue({} as never);
});

afterEach(cleanup);

it("展示已确认与候选记忆且不暴露内部标识", async () => {
  render(<ContextPage />);
  expect(await screen.findByText("偏好本地优先的工具")).toBeTruthy();
  fireEvent.click(screen.getByRole("tab", { name: /待确认/ }));
  const candidate = screen.getByDisplayValue("关注 Agent 工程岗位");
  fireEvent.change(candidate, { target: { value: "重点关注 Agent 平台工程岗位" } });
  expect(screen.queryByText("memory_1")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "确认" }));
  expect(reviewMemoryProposal).toHaveBeenCalledWith(
    "memory_proposal_1", "approved", "重点关注 Agent 平台工程岗位",
  );
});

it("手动输入只创建待确认提案", async () => {
  render(<ContextPage />);
  await screen.findByText("偏好本地优先的工具");
  fireEvent.change(screen.getByLabelText("记忆内容"), { target: { value: "偏好远程工作" } });
  fireEvent.click(screen.getByRole("button", { name: "加入待确认" }));
  expect(createMemoryProposal).toHaveBeenCalledWith("preference", "偏好远程工作");
});
