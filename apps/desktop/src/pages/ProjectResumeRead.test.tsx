// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { ProjectsPage } from "./ProjectsPage";
import { ResumePage } from "./ResumePage";

vi.mock("./ResumeStudioPanel", () => ({ ResumeStudioPanel: () => <div>高级修订编辑器</div> }));

afterEach(() => { cleanup(); vi.unstubAllGlobals(); delete window.__ACH_CONFIG__; });

function setup() {
  window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "read-client-test" };
  const fetcher = vi.fn();
  vi.stubGlobal("fetch", fetcher);
  return fetcher;
}

const project = {
  project: { project_id: "p1", revision: 2, display_name: "Agent Career Harness", created_by: "user", created_at: "2026-09-21" },
  evidence: [],
};
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });

it("默认列出并打开项目，无需输入内部 ID", async () => {
  const fetcher = setup()
    .mockResolvedValueOnce(response([project.project]))
    .mockResolvedValueOnce(response(project))
    .mockResolvedValueOnce(response([]));

  render(<ProjectsPage />);

  expect(await screen.findByRole("heading", { name: "Agent Career Harness" })).toBeTruthy();
  expect(screen.getByText("此项目尚无已记录证据。")).toBeTruthy();
  expect(screen.queryByLabelText(/项目 ID/)).toBeNull();
  expect(fetcher.mock.calls[0][0]).toBe("http://127.0.0.1:8765/api/v1/projects");
  expect(fetcher.mock.calls[1][0]).toBe("http://127.0.0.1:8765/api/v1/projects/p1");
  expect(fetcher.mock.calls[2][0]).toBe("http://127.0.0.1:8765/api/v1/github/projects/p1/analyses");
});

it("项目搜索只筛选已加载列表并保留清晰空状态", async () => {
  setup()
    .mockResolvedValueOnce(response([project.project]))
    .mockResolvedValueOnce(response(project))
    .mockResolvedValueOnce(response([]));
  render(<ProjectsPage />);
  await screen.findByRole("heading", { name: "Agent Career Harness" });

  fireEvent.change(screen.getByLabelText("搜索项目"), { target: { value: "不存在" } });
  expect(screen.getByText("没有匹配的项目。")).toBeTruthy();
});

it("GitHub 分析必须确认只读网络并保存可追溯档案", async () => {
  const fetcher = setup().mockImplementation(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/api/v1/projects")) return response([]);
    if (url.endsWith("/api/v1/github/analyze")) return response({ project_id: "github_p1" });
    throw new Error(`unexpected request ${url}`);
  });
  render(<ProjectsPage />);
  await screen.findByText("还没有项目档案");
  fireEvent.change(screen.getByLabelText("公开或私有仓库地址"), {
    target: { value: "https://github.com/example/career-tool" },
  });
  const submit = screen.getByRole("button", { name: "开始只读分析" });
  expect(submit.hasAttribute("disabled")).toBe(true);
  fireEvent.click(screen.getByText("我确认执行一次只读 GitHub 网络请求"));
  fireEvent.click(submit);
  expect(await screen.findByText(/只读分析完成/)).toBeTruthy();
  const call = fetcher.mock.calls.find(([url]) => String(url).endsWith("/api/v1/github/analyze"));
  expect(String(call?.[1]?.body)).toContain("confirm_read_only_network");
});

it("默认列出简历并读取基础内容与不可变修订", async () => {
  const base = { resume_id: "r1", candidate_id: "candidate_1", revision: 3, sections: { summary: "已确认内容" }, created_by: "user", created_at: "2026-09-21" };
  const revision = { revision_id: "rr1", resume_id: "r1", base_revision: 2, content: { summary: "目标版本" }, content_sha256: "a".repeat(64), accepted_patch_refs: [{ entity_id: "patch1", revision: 4 }], created_by: "user", created_at: "2026-09-21" };
  const fetcher = setup()
    .mockResolvedValueOnce(response([base]))
    .mockResolvedValueOnce(response(base))
    .mockResolvedValueOnce(response([revision]));
  fetcher.mockResolvedValueOnce(response([base]));

  render(<ResumePage />);

  expect(await screen.findByText("已确认内容")).toBeTruthy();
  expect(screen.getByText("目标版本")).toBeTruthy();
  expect(screen.getByText("来源基础版本：第 2 版")).toBeTruthy();
  expect(screen.queryByLabelText(/Resume Base ID|Resume Revision ID/)).toBeNull();
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(4));
  expect(fetcher.mock.calls.map((call) => call[0])).toEqual([
    "http://127.0.0.1:8765/api/v1/resumes",
    "http://127.0.0.1:8765/api/v1/resumes/r1/base",
    "http://127.0.0.1:8765/api/v1/resumes/r1/revisions",
    "http://127.0.0.1:8765/api/v1/resumes/r1/bases",
  ]);
});
