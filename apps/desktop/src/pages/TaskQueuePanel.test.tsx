// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { getTask, listTasks, retryTask, runTaskStage } from "../api/tasks";
import { TaskQueuePanel } from "./TaskQueuePanel";

vi.mock("../api/tasks", () => ({
  getTask: vi.fn(),
  listTasks: vi.fn(),
  retryTask: vi.fn(),
  runTaskStage: vi.fn(),
}));

const failedTask = {
  task_id: "task_sync_1",
  task_type: "source.github_sync",
  stage: "source_sync",
  status: "dead_letter" as const,
  progress: 0.4,
  current_attempt: 2,
  max_attempts: 2,
  version: 1,
  available_at: "2026-09-22T01:00:00Z",
  claimed_at: null,
  created_at: "2026-09-22T01:00:00Z",
  updated_at: "2026-09-22T01:02:00Z",
  last_error: "网络连接超时",
};

beforeEach(() => {
  vi.mocked(listTasks).mockResolvedValue([failedTask]);
  vi.mocked(getTask).mockResolvedValue({
    task: failedTask,
    attempts: [{
      task_id: failedTask.task_id,
      attempt: 2,
      task_version: 1,
      status: "failed",
      error_type: "TimeoutError",
      error_message: "网络连接超时",
      started_at: "2026-09-22T01:01:00Z",
      finished_at: "2026-09-22T01:02:00Z",
    }],
  });
  vi.mocked(retryTask).mockResolvedValue({
    ...failedTask,
    status: "pending",
    current_attempt: 2,
    max_attempts: 3,
    version: 2,
    last_error: null,
  });
  vi.mocked(runTaskStage).mockResolvedValue([{
    ...failedTask,
    status: "completed",
    progress: 1,
    current_attempt: 3,
    max_attempts: 3,
    version: 2,
    last_error: null,
  }]);
});

afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("展示失败原因、尝试记录并允许人工重试", async () => {
  render(<TaskQueuePanel />);
  expect(await screen.findByRole("heading", { name: "GitHub 只读同步" })).toBeTruthy();
  expect(screen.getByText(/最近错误：网络连接超时/)).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "查看尝试记录" }));
  expect(await screen.findByRole("region", { name: "GitHub 只读同步尝试记录" })).toBeTruthy();
  expect(screen.getByText(/第 2 次 · 失败 · 网络连接超时/)).toBeTruthy();

  fireEvent.click(screen.getByRole("button", { name: "人工重试" }));
  await waitFor(() => expect(retryTask).toHaveBeenCalledWith("task_sync_1"));
  await waitFor(() => expect(runTaskStage).toHaveBeenCalledWith("source_sync"));
  expect(screen.getByRole("status").textContent).toContain("人工重试已完成");
});
