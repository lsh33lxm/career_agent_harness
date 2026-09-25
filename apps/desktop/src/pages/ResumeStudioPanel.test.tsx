// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { ResumeStudioPanel } from "./ResumeStudioPanel";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.localStorage.clear();
  delete window.__ACH_CONFIG__;
});

const response = (body: unknown, mediaType = "application/json") => new Response(
  mediaType === "application/json" ? JSON.stringify(body) : body as BodyInit,
  { status: 200, headers: { "Content-Type": mediaType } },
);

it("creates a user target profile, renders preview, shows ATS gaps and authenticates download", async () => {
  window.__ACH_CONFIG__ = {
    apiBaseUrl: "http://127.0.0.1:8765",
    launchToken: "resume-ui-token",
  };
  const fetcher = vi.fn()
    .mockResolvedValueOnce(response([
      {
        template_id: "resume-render-html", name: "观复简历 / Warm Paper",
        version: "1.0.0", renderer: "html_css", content_sha256: "a".repeat(64),
        description: "内置本地渲染器", status: "active", created_at: "now",
      },
      {
        template_id: "resume-render-typst", name: "观复简历 / Typst A4",
        version: "1.0.0", renderer: "typst_worker", content_sha256: "b".repeat(64),
        description: "Isolated", status: "disabled", created_at: "now",
      },
    ]))
    .mockResolvedValueOnce(response([
      { resume_id: "resume_001", revision: 2, candidate_id: "candidate_1", sections: {}, created_at: "now", created_by: "user" },
    ]))
    .mockResolvedValueOnce(response([
      { revision_id: "resume_revision_001", resume_id: "resume_001", base_revision: 2, content: { summary: "经历" }, content_sha256: "c".repeat(64), accepted_patch_refs: [], created_at: "now", created_by: "user" },
    ]))
    .mockResolvedValueOnce(response({
      target_profile_id: "target_profile_001", resume_id: "resume_001",
      title: "Platform Engineer", company: null, opportunity_id: null,
      opportunity_revision: null, requirement_refs: [], keyword_gaps: [],
      status: "approved", created_by: "user", created_at: "now",
    }))
    .mockResolvedValueOnce(response({
      render_run_id: "render_001", resume_revision_id: "resume_revision_001",
      target_profile_id: "target_profile_001", template_id: "resume-render-html",
      template_version: "1.0.0", renderer: "html_css",
      renderer_plugin_id: "resume-render-html-builtin", renderer_plugin_version: "1.0.0",
      input_sha256: "b".repeat(64),
      status: "completed", output_artifact_id: "artifact_001",
      output_sha256: "a".repeat(64), output_media_type: "application/pdf",
      page_count: 1, preview_html: "<article class=\"resume\"><h1>Minnn</h1></article>",
      checks: { text_layer: true }, created_by: "user", created_at: "now",
    }))
    .mockResolvedValueOnce(response({
      render_run_id: "render_001", status: "warnings", page_count: 1,
      checks: { text_layer: true }, keyword_gaps: ["Kubernetes"], created_at: "now",
    }))
    .mockResolvedValueOnce(response(new Blob(["%PDF"]), "application/pdf"))
    .mockResolvedValueOnce(response({
      render_run_id: "render_001", decision: "approved", reviewer: "user",
      reason: "已核对内容与版式", reviewed_at: "now",
    }));
  vi.stubGlobal("fetch", fetcher);
  const createObjectURL = vi.fn(() => "blob:resume");
  const revokeObjectURL = vi.fn();
  Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
  Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => undefined);

  render(<ResumeStudioPanel />);
  fireEvent.focus(screen.getByLabelText("渲染模板"));
  expect(await screen.findByRole("option", { name: /Typst A4/ })).toBeTruthy();
  fireEvent.focus(screen.getByLabelText("基础简历"));
  await waitFor(() => expect(fetcher).toHaveBeenCalledTimes(2));
  fireEvent.change(screen.getByLabelText("基础简历"), { target: { value: "resume_001" } });
  expect(await screen.findByRole("option", { name: /resume_revision_001/ })).toBeTruthy();
  expect((screen.getByLabelText("目标岗位档案精确引用") as HTMLInputElement).value).toMatch(/^target_profile_/);
  fireEvent.change(screen.getByLabelText("已审核修订"), { target: { value: "resume_revision_001" } });
  fireEvent.change(screen.getByLabelText("目标岗位档案精确引用"), { target: { value: "target_profile_001" } });
  fireEvent.change(screen.getByLabelText("目标岗位"), { target: { value: "Platform Engineer" } });
  fireEvent.click(screen.getByRole("button", { name: "保存目标岗位" }));
  expect(await screen.findByText(/目标岗位已保存/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "生成预览与 PDF" }));
  expect(await screen.findByText("Minnn")).toBeTruthy();
  expect(screen.getByText(/Kubernetes/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "下载 PDF" }));
  await waitFor(() => expect(createObjectURL).toHaveBeenCalled());
  fireEvent.change(screen.getByLabelText("审核理由"), { target: { value: "已核对内容与版式" } });
  fireEvent.click(screen.getByRole("button", { name: "批准" }));
  expect(await screen.findByText(/已由用户已批准/)).toBeTruthy();
  expect(fetcher.mock.calls[6][1].headers.get("Authorization")).toBe("Bearer resume-ui-token");
  expect(createObjectURL).toHaveBeenCalled();
  expect(window.localStorage.getItem("ach.resume-studio.draft.v1")).toContain("resume_001");
});

it("supports local draft undo and redo without changing Career Core", () => {
  window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "resume-ui-token" };
  vi.stubGlobal("fetch", vi.fn());
  render(<ResumeStudioPanel />);
  const editor = screen.getByLabelText("简历建议草稿");
  fireEvent.change(editor, { target: { value: '{"summary":"第一版"}' } });
  fireEvent.change(editor, { target: { value: '{"summary":"第二版"}' } });
  fireEvent.click(screen.getByRole("button", { name: "撤销" }));
  expect((editor as HTMLTextAreaElement).value).toBe('{"summary":"第一版"}');
  fireEvent.click(screen.getByRole("button", { name: "重做" }));
  expect((editor as HTMLTextAreaElement).value).toBe('{"summary":"第二版"}');
});

it("edits scalar resume fields while preserving the JSON round trip", () => {
  window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "resume-ui-token" };
  vi.stubGlobal("fetch", vi.fn());
  render(<ResumeStudioPanel />);
  const editor = screen.getByLabelText("简历建议草稿");
  fireEvent.change(editor, { target: { value: '{"summary":"原始摘要","unknownField":{"keep":true}}' } });
  fireEvent.change(screen.getByLabelText("简历字段 summary"), { target: { value: "更新后的摘要" } });
  expect((screen.getByLabelText("简历建议草稿") as HTMLTextAreaElement).value).toContain("更新后的摘要");
  expect((screen.getByLabelText("简历建议草稿") as HTMLTextAreaElement).value).toContain("unknownField");
});

it("edits array resume entries without dropping unknown fields", () => {
  window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "resume-ui-token" };
  vi.stubGlobal("fetch", vi.fn());
  render(<ResumeStudioPanel />);
  const editor = screen.getByLabelText("简历建议草稿");
  fireEvent.change(editor, { target: { value: '{"projects":[{"title":"原项目","url":"keep"}],"custom":{"keep":true}}' } });
  fireEvent.change(screen.getByLabelText("简历字段 projects 第 1 项"), { target: { value: "更新后的项目" } });
  const value = (editor as HTMLTextAreaElement).value;
  expect(value).toContain("更新后的项目");
  expect(value).toContain('"url": "keep"');
  expect(value).toContain('"custom"');
});
