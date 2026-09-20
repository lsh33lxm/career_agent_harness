// @vitest-environment jsdom
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { ProjectsPage } from "./ProjectsPage";
import { ResumePage } from "./ResumePage";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); delete window.__ACH_CONFIG__; });
function setup() {
  window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "read-client-test" };
  const fetcher = vi.fn(); vi.stubGlobal("fetch", fetcher); return fetcher;
}
const project = { project: { project_id: "p1", revision: 2, display_name: "Project One", created_by: "user", created_at: "2026-09-21" }, evidence: [] };
const response = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status });
it("does not query before explicit input and keeps project revision distinct from evidence versions", async () => {
  const fetcher = setup().mockResolvedValue(response(project));
  render(<ProjectsPage />);
  expect(fetcher).not.toHaveBeenCalled();
  expect(screen.queryByText("此项目尚无已记录证据。")).toBeNull();
  fireEvent.change(screen.getByLabelText("项目 ID"), { target: { value: "p1" } });
  fireEvent.change(screen.getByLabelText("项目 修订（留空读取最新）"), { target: { value: "2" } });
  fireEvent.click(screen.getByRole("button", { name: "读取项目" }));
  expect(await screen.findByText("Project One")).toBeTruthy();
  expect(screen.getByText(/不代表所选项目修订当时/)).toBeTruthy();
  expect(fetcher.mock.calls[0][0]).toBe("http://127.0.0.1:8765/api/v1/projects/p1?revision=2");
  expect(fetcher.mock.calls[0][1].method).toBeUndefined();
});
it("shows missing and retries the submitted ID even after input changes", async () => {
  const fetcher = setup().mockResolvedValueOnce(response({ detail: "missing" }, 404)).mockResolvedValueOnce(response(project));
  render(<ProjectsPage />);
  fireEvent.change(screen.getByLabelText("项目 ID"), { target: { value: "p1" } });
  fireEvent.click(screen.getByRole("button", { name: "读取项目" }));
  expect(await screen.findByText("未找到指定记录或修订。")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("项目 ID"), { target: { value: "other" } });
  fireEvent.click(screen.getByRole("button", { name: "重试项目" }));
  expect(await screen.findByText("Project One")).toBeTruthy();
  expect(fetcher.mock.calls[1][0]).toContain("/p1");
});
it("ignores stale responses after a new explicit query", async () => {
  let finish!: (response: Response) => void;
  setup().mockReturnValueOnce(new Promise((resolve) => { finish = resolve; })).mockResolvedValueOnce(response(project));
  render(<ProjectsPage />);
  fireEvent.change(screen.getByLabelText("项目 ID"), { target: { value: "old" } });
  fireEvent.click(screen.getByRole("button", { name: "读取项目" }));
  expect(screen.getByRole("status")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("项目 ID"), { target: { value: "p1" } });
  fireEvent.click(screen.getByRole("button", { name: "读取项目" }));
  expect(await screen.findByText("Project One")).toBeTruthy();
  await act(async () => finish(response({ ...project, project: { ...project.project, display_name: "Stale" } })));
  expect(screen.queryByText("Stale")).toBeNull();
});
it("separates Resume Base and immutable revision with exact patch references", async () => {
  const fetcher = setup().mockResolvedValueOnce(response({ resume_id: "r1", candidate_id: "candidate_1", revision: 3, sections: { summary: "Confirmed content" }, created_by: "user", created_at: "now" }))
    .mockResolvedValueOnce(response({ revision_id: "rr1", resume_id: "r1", base_revision: 2, content: {}, content_sha256: "a".repeat(64), accepted_patch_refs: [{ entity_id: "patch1", revision: 4 }], created_by: "user", created_at: "then" }));
  render(<ResumePage />);
  expect(fetcher).not.toHaveBeenCalled();
  fireEvent.change(screen.getByLabelText("Resume Base ID"), { target: { value: "r1" } });
  fireEvent.click(screen.getByRole("button", { name: "读取Resume Base" }));
  expect(await screen.findByText("候选人：candidate_1")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Resume Revision ID"), { target: { value: "rr1" } });
  fireEvent.click(screen.getByRole("button", { name: "读取Resume Revision" }));
  expect(await screen.findByText("patch1#4")).toBeTruthy();
  expect(screen.getByText("来源 Base：r1#2")).toBeTruthy();
  expect(screen.getByText("r1#3")).toBeTruthy();
  expect(screen.getByText("该记录内容为空。")).toBeTruthy();
  expect(fetcher.mock.calls.every((call) => call[1].method === undefined)).toBe(true);
});
