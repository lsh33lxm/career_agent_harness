// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter } from "react-router-dom";

import { admitStagedJob } from "../api/jobRadar";
import { approveDemoResume, createDemoResumeRevision, startDemoLoop } from "../api/demoLoop";
import { getDemoStory, type DemoStory } from "../api/demoStory";
import {
  getLegacyImportStatus,
  getLegacyJob,
  listLegacyJobs,
  runLegacyImport,
  type LegacyImportReport,
  type LegacyJobSummary,
} from "../api/legacy";
import { JobRadarPanel } from "./JobRadarPanel";

vi.mock("../api/jobRadar", () => ({ admitStagedJob: vi.fn() }));
vi.mock("../api/demoLoop", () => ({ approveDemoResume: vi.fn(), createDemoResumeRevision: vi.fn(), startDemoLoop: vi.fn() }));
vi.mock("../api/demoStory", () => ({ getDemoStory: vi.fn() }));
vi.mock("../api/legacy", () => ({
  getLegacyImportStatus: vi.fn(),
  getLegacyJob: vi.fn(),
  listLegacyJobs: vi.fn(),
  runLegacyImport: vi.fn(),
}));

const job: LegacyJobSummary = {
  staging_id: "staging_001",
  title: "Agent Harness 工程师",
  company: "观复科技",
  location: '["北京", "远程"]',
  salary: "30-45K",
  source_url: "https://example.com/jobs/1",
  status: "staged",
  duplicate_of: null,
  suggested_score: 0.86,
  review_status: "historical_unconfirmed",
  source_path: "data/统一数据/岗位与JD数据.csv",
  source_class: "job",
  source_sha256: "a".repeat(64),
  row_number: 161,
  imported_at: "2026-09-21T10:00:00Z",
  tags: ['["Python", "React"]'],
};

const report: LegacyImportReport = {
  batch_id: "batch_001",
  source_root: "D:/legacy",
  source_signature_before: "before",
  source_signature_after: "before",
  status: "completed",
  started_at: "2026-09-21T10:00:00Z",
  finished_at: "2026-09-21T10:01:00Z",
  files: [],
  totals: { read_count: 7575, new_count: 1028, duplicate_count: 684, failed_count: 0 },
  importer_version: "1.0",
};

beforeEach(() => {
  vi.mocked(getLegacyImportStatus).mockReset().mockResolvedValue({
    configured_source_root: "D:/legacy",
    source_accessible: true,
    latest_report: report,
  });
  vi.mocked(listLegacyJobs).mockReset().mockResolvedValue([job]);
  vi.mocked(getLegacyJob).mockReset().mockResolvedValue({
    job,
    jd_text: "负责 <b>Agent Harness</b> 平台开发",
    raw_record: {},
    transform: {},
    batch_id: "batch_001",
    related_interviews: [{ title: "技术一面", interview_date: "2026-09-18" }],
  });
  vi.mocked(runLegacyImport).mockReset().mockResolvedValue(report);
  vi.mocked(admitStagedJob).mockReset().mockResolvedValue({});
  vi.mocked(startDemoLoop).mockReset();
  vi.mocked(approveDemoResume).mockReset();
  vi.mocked(createDemoResumeRevision).mockReset();
  vi.mocked(getDemoStory).mockReset().mockResolvedValue({ available: false, steps: [], events: [], links: [] });
});

afterEach(cleanup);

describe("JobRadarPanel", () => {
  it("默认展示真实岗位并可搜索和查看来源溯源", async () => {
    render(<MemoryRouter><JobRadarPanel /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Agent Harness 工程师" })).toBeTruthy();
    expect(screen.getByText("北京、远程 · 30-45K")).toBeTruthy();
    expect(screen.getByText("Python")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("搜索岗位、公司或技能"), {
      target: { value: "Python" },
    });
    fireEvent.click(screen.getByRole("button", { name: "搜索" }));
    await waitFor(() => expect(listLegacyJobs).toHaveBeenLastCalledWith(
      expect.objectContaining({ query: "Python", limit: 100 }),
    ));

    fireEvent.click(screen.getAllByRole("button", { name: "查看详情" })[0]);
    expect(await screen.findByText("data/统一数据/岗位与JD数据.csv")).toBeTruthy();
    expect(screen.getByText("161")).toBeTruthy();
    expect(screen.getByText("技术一面 · 2026-09-18")).toBeTruthy();
    expect(screen.getByText(/负责 Agent Harness 平台开发/)).toBeTruthy();
  });

  it("由用户触发可审计导入并明确加入求职流程", async () => {
    render(<MemoryRouter><JobRadarPanel /></MemoryRouter>);
    await screen.findByRole("heading", { name: "Agent Harness 工程师" });
    fireEvent.click(screen.getByRole("button", { name: "重新核验导入" }));
    await waitFor(() => expect(runLegacyImport).toHaveBeenCalledWith("D:/legacy"));
    fireEvent.click(screen.getByRole("button", { name: "加入求职流程" }));
    await waitFor(() => expect(admitStagedJob).toHaveBeenCalledWith("staging_001"));
  });

  it("演示模式保存逐条审核，并只在全部审核后请求生成版本", async () => {
    window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "demo", demoMode: true };
    const patch = {
      patch_id: "patch_demo_1", revision: 1, review_status: "proposed" as const,
      reviewed_at: null, review_source: "本地演示草稿 / 待人工审核", review_note: null,
      operations: [{ before: "旧摘要", after: "建议摘要", target_path: "/summary", reason: "待核对", requirement_ids: ["req_1"], evidence_ids: ["evidence_1"] }],
    };
    const story = { available: true, staging_id: "staging_demo", opportunity_id: "op_demo", application_id: "app_demo", resume_revision_id: null, application_state: "preparing", resume_patches: [patch], steps: [], events: [], links: [] };
    vi.mocked(getDemoStory).mockResolvedValueOnce({ available: false, steps: [], events: [], links: [] }).mockResolvedValue(story);
    vi.mocked(startDemoLoop).mockResolvedValue({ staging_id: "staging_demo", opportunity_id: "op_demo", application_id: "app_demo", application_state: "preparing", patch_id: patch.patch_id, resume_revision_id: "", interview_id: null, interview_revision: null, interview_prep_proposal_id: null, interview_feedback_proposal_id: null });
    vi.mocked(approveDemoResume).mockResolvedValue({ patch_id: patch.patch_id, review_status: "accepted", reviewed_at: "now", review_source: "用户审核", review_note: "审核", evidence_ids: ["evidence_1"] });
    vi.mocked(createDemoResumeRevision).mockResolvedValue({ resume_revision_id: "revision_1", application_id: "app_demo" });

    render(<MemoryRouter><JobRadarPanel /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "开始演示闭环" }));
    fireEvent.click(await screen.findByRole("button", { name: "接受" }));
    await waitFor(() => expect(approveDemoResume).toHaveBeenCalledWith("patch_demo_1", "app_demo", "accepted", undefined));
    expect(createDemoResumeRevision).not.toHaveBeenCalled();
    expect(screen.getByText(/不证明个人经历或技能/)).toBeTruthy();
  });

  it("完成接受、拒绝和手动编辑后生成并展示申请引用的版本", async () => {
    window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "demo", demoMode: true };
    const story: DemoStory = {
      available: true,
      staging_id: "staging_demo",
      opportunity_id: "op_demo",
      application_id: "app_demo",
      resume_revision_id: null,
      application_state: "preparing",
      evidence_ref_id: "evidence_job_1",
      requirements: [{ requirement_id: "req_1", requirement_text: "Agent 平台经验", status: "proposed" }],
      resume_patches: [
        { patch_id: "patch_accept", revision: 1, review_status: "proposed", reviewed_at: null, review_source: "本地演示草稿 / 待人工审核", review_note: null, operations: [{ before: "旧摘要", after: "建议摘要", target_path: "/summary", reason: "对应岗位要求", requirement_ids: ["req_1"], evidence_ids: ["evidence_job_1"] }] },
        { patch_id: "patch_reject", revision: 1, review_status: "proposed", reviewed_at: null, review_source: "本地演示草稿 / 待人工审核", review_note: null, operations: [{ before: "旧技能", after: "建议技能", target_path: "/skills/0", reason: "待核对技能", requirement_ids: ["req_1"], evidence_ids: ["evidence_job_1"] }] },
        { patch_id: "patch_edit", revision: 1, review_status: "proposed", reviewed_at: null, review_source: "本地演示草稿 / 待人工审核", review_note: null, operations: [{ before: "旧经历", after: "建议经历", target_path: "/experience/0", reason: "待人工确认", requirement_ids: ["req_1"], evidence_ids: ["evidence_job_1"] }] },
      ],
      steps: [], events: [], links: [],
    };
    const unavailable: DemoStory = { available: false, steps: [], events: [], links: [] };
    let initialRead = true;
    vi.mocked(getDemoStory).mockImplementation(async () => {
      if (initialRead) {
        initialRead = false;
        return unavailable;
      }
      return structuredClone(story);
    });
    vi.mocked(startDemoLoop).mockResolvedValue({ staging_id: "staging_demo", opportunity_id: "op_demo", application_id: "app_demo", application_state: "preparing", patch_id: "patch_accept", resume_revision_id: "", interview_id: null, interview_revision: null, interview_prep_proposal_id: null, interview_feedback_proposal_id: null });
    vi.mocked(approveDemoResume).mockImplementation(async (patchId, _applicationId, decision, editedValue) => {
      const patch = story.resume_patches?.find((item) => item.patch_id === patchId);
      if (patch) {
        patch.review_status = decision;
        patch.reviewed_at = "2026-09-23T12:00:00Z";
        patch.review_source = editedValue === undefined ? "用户审核" : "用户手动编辑";
        if (editedValue !== undefined && patch.operations[0]) patch.operations[0].after = editedValue;
      }
      return { patch_id: patchId, review_status: decision, reviewed_at: "2026-09-23T12:00:00Z", review_source: "用户审核", review_note: "已审核", evidence_ids: ["evidence_job_1"] };
    });
    vi.mocked(createDemoResumeRevision).mockImplementation(async () => {
      story.resume_revision_id = "resume_revision_1";
      return { resume_revision_id: "resume_revision_1", application_id: "app_demo" };
    });

    render(<MemoryRouter><JobRadarPanel /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "开始演示闭环" }));
    expect(await screen.findByText("Agent 平台经验 · req_1 · proposed")).toBeTruthy();
    expect(screen.getByText("岗位 Evidence：evidence_job_1")).toBeTruthy();
    expect(screen.queryByRole("button", { name: "生成目标 ResumeRevision" })).toBeNull();
    fireEvent.change(screen.getAllByRole("textbox", { name: "手动编辑（用户内容）" })[2], { target: { value: "用户核实后的经历" } });

    fireEvent.click(screen.getAllByRole("button", { name: "接受" })[0]);
    await waitFor(() => expect(approveDemoResume).toHaveBeenCalledWith("patch_accept", "app_demo", "accepted", undefined));
    expect(screen.queryByRole("button", { name: "生成目标 ResumeRevision" })).toBeNull();
    fireEvent.click(screen.getAllByRole("button", { name: "拒绝" })[0]);
    await waitFor(() => expect(approveDemoResume).toHaveBeenCalledWith("patch_reject", "app_demo", "rejected", undefined));
    const editedPatch = screen.getByText(/Patch patch_edit/).closest("article");
    if (!editedPatch) throw new Error("manual edit Patch article was not rendered");
    fireEvent.click(within(editedPatch).getByRole("button", { name: "保存手动编辑并接受" }));
    await waitFor(() => expect(approveDemoResume).toHaveBeenCalledWith("patch_edit", "app_demo", "accepted", "用户核实后的经历"));

    fireEvent.click(await screen.findByRole("button", { name: "生成目标 ResumeRevision" }));
    await waitFor(() => expect(createDemoResumeRevision).toHaveBeenCalledWith("app_demo"));
    expect(await screen.findByText("已生成版本：resume_revision_1 · 申请：app_demo · 状态仍为准备中")).toBeTruthy();
    expect(screen.getByRole("link", { name: "申请与历史" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "知识追溯" })).toBeTruthy();
  });

  it("审核保存失败时提示恢复方式且不显示成功状态", async () => {
    window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "demo", demoMode: true };
    const story: DemoStory = {
      available: true, staging_id: "staging_demo", opportunity_id: "op_demo", application_id: "app_demo",
      resume_revision_id: null, application_state: "preparing", steps: [], events: [], links: [],
      resume_patches: [{ patch_id: "patch_failure", revision: 1, review_status: "proposed", reviewed_at: null, review_source: "本地演示草稿 / 待人工审核", review_note: null,
        operations: [{ before: "旧摘要", after: "建议摘要", target_path: "/summary", reason: "待核对", requirement_ids: ["req_1"], evidence_ids: ["evidence_1"] }] }],
    };
    let initialRead = true;
    vi.mocked(getDemoStory).mockImplementation(async () => {
      if (initialRead) {
        initialRead = false;
        return { available: false, steps: [], events: [], links: [] };
      }
      return structuredClone(story);
    });
    vi.mocked(startDemoLoop).mockResolvedValue({ staging_id: "staging_demo", opportunity_id: "op_demo", application_id: "app_demo", application_state: "preparing", patch_id: "patch_failure", resume_revision_id: "", interview_id: null, interview_revision: null, interview_prep_proposal_id: null, interview_feedback_proposal_id: null });
    vi.mocked(approveDemoResume).mockRejectedValue(new Error("本地保存失败"));

    render(<MemoryRouter><JobRadarPanel /></MemoryRouter>);
    fireEvent.click(await screen.findByRole("button", { name: "开始演示闭环" }));
    fireEvent.click(await screen.findByRole("button", { name: "接受" }));
    expect((await screen.findByRole("status")).textContent).toContain("本地保存失败");
    expect(screen.getByRole("status").textContent).toContain("可重试");
    expect(screen.getByRole("heading", { name: "Patch patch_failure · 待审核" })).toBeTruthy();
    expect(screen.queryByText(/审核已写入本地演示数据库/)).toBeNull();
  });
});
