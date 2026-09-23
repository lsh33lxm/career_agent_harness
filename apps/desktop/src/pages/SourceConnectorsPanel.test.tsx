// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import {
  createLocalFolderConnector,
  listSourceConnectors,
  listSourceSyncRuns,
  setSourceConnectorPaused,
  syncSourceConnector,
  testSourceConnector,
} from "../api/sourceConnectors";
import { SourceConnectorsPanel } from "./SourceConnectorsPanel";

vi.mock("../api/sourceConnectors", () => ({
  createLocalFolderConnector: vi.fn(),
  listSourceConnectors: vi.fn(),
  listSourceSyncRuns: vi.fn(),
  setSourceConnectorPaused: vi.fn(),
  syncSourceConnector: vi.fn(),
  testSourceConnector: vi.fn(),
}));

const connector = {
  connector_id: "connector_local_1",
  connector_type: "local_folder" as const,
  display_name: "我的求职资料",
  status: "active" as const,
  config: { root_path: "D:\\求职资料" },
  sync_cursor: null,
  conflict_policy: "defer" as const,
  delete_policy: "mark_deleted" as const,
  created_at: "2026-09-22T00:00:00Z",
  updated_at: "2026-09-22T00:00:00Z",
};

beforeEach(() => {
  vi.mocked(listSourceConnectors).mockResolvedValue([connector]);
  vi.mocked(listSourceSyncRuns).mockResolvedValue([]);
  vi.mocked(testSourceConnector).mockResolvedValue({ ok: true, connector_type: "local_folder" });
  vi.mocked(syncSourceConnector).mockResolvedValue({ status: "completed", last_error: null });
  vi.mocked(setSourceConnectorPaused).mockResolvedValue({ ...connector, status: "paused" });
  vi.mocked(createLocalFolderConnector).mockResolvedValue(connector);
});

afterEach(() => { cleanup(); vi.clearAllMocks(); });

it("展示中文资料源并允许测试、同步和暂停", async () => {
  render(<SourceConnectorsPanel />);
  expect(await screen.findByText("我的求职资料")).toBeTruthy();
  expect(screen.queryByText("connector_local_1")).toBeNull();

  fireEvent.click(screen.getByRole("button", { name: "测试连接" }));
  expect(await screen.findByText(/连接正常/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /立即同步/ }));
  expect(await screen.findByText(/同步完成/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /暂停/ }));
  await waitFor(() => expect(setSourceConnectorPaused).toHaveBeenCalledWith("connector_local_1", true));
});

it("通过名称和路径创建本地资料源", async () => {
  vi.mocked(listSourceConnectors).mockResolvedValueOnce([]).mockResolvedValue([connector]);
  render(<SourceConnectorsPanel />);
  await screen.findByText(/尚未添加资料源/);
  fireEvent.change(screen.getByLabelText("资料源名称"), { target: { value: "求职档案" } });
  fireEvent.change(screen.getByLabelText("本地文件夹路径"), { target: { value: "D:\\档案" } });
  fireEvent.click(screen.getByRole("button", { name: "添加资料源" }));
  await waitFor(() => expect(createLocalFolderConnector).toHaveBeenCalledWith("求职档案", "D:\\档案"));
});

it("正确展示 Legacy 与 GitHub 资料源并区分网络验证状态", async () => {
  vi.mocked(listSourceConnectors).mockResolvedValue([
    {
      ...connector,
      connector_id: "connector_legacy_1",
      connector_type: "legacy_agent_radar",
      display_name: "历史岗位",
      config: { root_path: "D:\\历史数据" },
    },
    {
      ...connector,
      connector_id: "connector_github_1",
      connector_type: "github",
      display_name: "项目仓库",
      config: { repository_url: "https://github.com/example/career-tool" },
    },
  ]);
  vi.mocked(testSourceConnector).mockResolvedValue({
    ok: true,
    connector_type: "github",
    network_verified: false,
  });
  render(<SourceConnectorsPanel />);

  expect(await screen.findByText(/Legacy 历史数据/)).toBeTruthy();
  expect(screen.getByText(/GitHub 只读仓库/)).toBeTruthy();
  const githubCard = screen.getByText("项目仓库").closest("article");
  if (!githubCard) throw new Error("GitHub connector card not found");
  fireEvent.click(within(githubCard).getByRole("button", { name: "测试连接" }));
  expect(await screen.findByText(/尚未完成真实只读网络验证/)).toBeTruthy();
});
