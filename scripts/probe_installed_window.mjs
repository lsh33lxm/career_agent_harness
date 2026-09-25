import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";

const port = process.env.CDP_PORT ?? "9231";
const artifactDir = process.env.INSTALLED_WINDOW_ARTIFACT_DIR ?? "artifacts/verification/installed-window-e2e-current";
const useFixture = process.env.INSTALLED_WINDOW_USE_FIXTURE === "1";
await mkdir(artifactDir, { recursive: true });
const browser = await chromium.connectOverCDP(`http://127.0.0.1:${port}`);
const contexts = browser.contexts();
const pages = contexts.flatMap((context) => context.pages());
console.log(JSON.stringify({
  contexts: contexts.length,
  pages: pages.map((page) => ({ url: page.url(), title: page.title() })),
}, null, 2));
const page = pages.find((candidate) => candidate.url().includes("tauri.localhost")) ?? pages[0];
if (!page) throw new Error("No installed WebView page found");
const internals = await page.evaluate(() => ({
  hasTauriInternals: Boolean(window.__TAURI_INTERNALS__),
  keys: window.__TAURI_INTERNALS__ ? Object.keys(window.__TAURI_INTERNALS__) : [],
  body: document.body.innerText.slice(0, 160),
}));
console.log(JSON.stringify(internals, null, 2));

// Exercise the installed Applications and Interview workspace with deterministic
// local responses. Domain transition rules are covered by backend tests; this
// fixture proves the packaged WebView invokes those commands and renders their
// projections without sending an external submission.
let application = {
  entity_id: "application_installed_e2e",
  revision: 1,
  state: "preparing",
  opportunity_id: "opportunity_installed_e2e",
  opportunity_revision: 1,
  resume_revision_id: null,
  submitted_at: null,
  submission_authority: null,
};
let interview = null;
const resumeBase = {
  resume_id: "resume_base_installed_e2e",
  revision: 1,
  candidate_id: "candidate_installed_e2e",
  sections: { basics: { name: "安装验收候选人" } },
  created_at: "2026-09-25T00:00:00Z",
  created_by: "user",
};
const resumeRevision = {
  revision_id: "resume_revision_installed_e2e",
  resume_id: resumeBase.resume_id,
  base_revision: 1,
  content: { name: "安装验收候选人", summary: "原始本地简历摘要" },
  content_sha256: "d".repeat(64),
  accepted_patch_refs: [],
  created_at: "2026-09-25T00:00:00Z",
  created_by: "user",
};
let studioRevision = resumeRevision;
let renderRun = null;
const demoPatchState = [
  { patch_id: "patch_installed_accept", review_status: "proposed", operations: [{ before: "原摘要", after: "平台工程经历", reason: "与岗位要求关联", requirement_ids: ["requirement_installed_1"], evidence_ids: ["evidence_installed_1"] }] },
  { patch_id: "patch_installed_reject", review_status: "proposed", operations: [{ before: "旧技能", after: "未经证实技能", reason: "待人工判断", requirement_ids: ["requirement_installed_2"], evidence_ids: [] }] },
  { patch_id: "patch_installed_edit", review_status: "proposed", operations: [{ before: "原项目", after: "项目经历建议", reason: "岗位匹配建议", requirement_ids: ["requirement_installed_3"], evidence_ids: ["evidence_installed_2"] }] },
];
let demoRevisionId = null;
function demoStory() {
  return {
    available: true,
    staging_id: "staging_installed_demo",
    opportunity_id: "opportunity_installed_demo",
    application_id: "application_installed_demo",
    resume_revision_id: demoRevisionId,
    application_state: "preparing",
    application_revision: 1,
    evidence_ref_id: "evidence_installed_1",
    requirements: [{ requirement_id: "requirement_installed_1", requirement_text: "熟悉 Python", status: "accepted" }],
    resume_patches: demoPatchState,
    steps: [], events: [], links: [],
  };
}
const fulfillJson = (route, body, status = 200) => route.fulfill({
  status,
  contentType: "application/json",
  body: JSON.stringify(body),
});
if (useFixture) {
await page.route("**/api/v1/applications", async (route) => {
  if (route.request().method() === "GET") return fulfillJson(route, [application]);
  return route.continue();
});
await page.route("**/api/v1/career-loop/demo-start", async (route) => fulfillJson(route, { staging_id: "staging_installed_demo", opportunity_id: "opportunity_installed_demo", application_id: "application_installed_demo", application_state: "preparing", patch_id: demoPatchState[0].patch_id, resume_revision_id: "", interview_id: null, interview_revision: null, interview_prep_proposal_id: null, interview_feedback_proposal_id: null }, 201));
await page.route("**/api/v1/career-loop/demo-story", async (route) => fulfillJson(route, demoStory()));
await page.route("**/api/v1/career-loop/demo-approve-resume", async (route) => {
  const body = JSON.parse(route.request().postData() ?? "{}");
  const patch = demoPatchState.find((item) => item.patch_id === body.patch_id);
  if (patch) patch.review_status = body.decision;
  return fulfillJson(route, { patch_id: body.patch_id, review_status: body.decision, reviewed_at: "2026-09-25T00:00:00Z", review_source: "user", review_note: "安装版 fixture 用户决定", evidence_ids: [] });
});
await page.route("**/api/v1/career-loop/demo-resume-revision", async (route) => {
  demoRevisionId = "resume_revision_installed_demo";
  return fulfillJson(route, { resume_revision_id: demoRevisionId, application_id: "application_installed_demo" }, 201);
});
await page.route("**/api/v1/applications/application_installed_e2e/interviews", async (route) => fulfillJson(route, interview ? [interview] : []));
await page.route("**/api/v1/resumes", async (route) => {
  if (route.request().method() === "GET") return fulfillJson(route, [resumeBase]);
  return route.continue();
});
await page.route("**/api/v1/resumes/resume_base_installed_e2e/revisions", async (route) => fulfillJson(route, [resumeRevision]));
await page.route("**/api/v1/resume/revisions/resume_revision_installed_e2e", async (route) => fulfillJson(route, studioRevision));
await page.route("**/api/v1/resume-revisions/resume_revision_installed_e2e", async (route) => fulfillJson(route, studioRevision));
await page.route("**/api/v1/resume/revisions/resume_revision_installed_e2e_v2", async (route) => fulfillJson(route, studioRevision));
await page.route("**/api/v1/resume/templates", async (route) => fulfillJson(route, [{ template_id: "resume-render-html", name: "观复简历 / 暖纸", version: "1.0.0", renderer: "html_css", content_sha256: "e".repeat(64), description: "内置本地渲染器", status: "active", created_at: "2026-09-25T00:00:00Z" }]));
await page.route("**/api/v1/resume/target-profiles", async (route) => fulfillJson(route, { target_profile_id: "target_profile_installed_e2e", resume_id: resumeBase.resume_id, title: "平台工程实习生", company: "腾讯", opportunity_id: null, opportunity_revision: null, requirement_refs: [], keyword_gaps: [], status: "active", created_by: "user", created_at: "2026-09-25T00:00:00Z" }, 201));
await page.route("**/api/v1/resume/patch-proposals", async (route) => fulfillJson(route, { patch_id: "resume_patch_installed_e2e", revision: 1, status: "proposed" }, 201));
await page.route("**/api/v1/resume/patches/*/review", async (route) => {
  const patchId = route.request().url().split("/patches/")[1].split("/")[0];
  return fulfillJson(route, { patch_id: patchId, revision: 2, status: "accepted" });
});
await page.route("**/api/v1/resume/revisions", async (route) => {
  studioRevision = { ...studioRevision, revision_id: "resume_revision_installed_e2e_v2", content: { ...studioRevision.content, summary: "已由用户确认的平台工程实习经历" }, accepted_patch_refs: [{ entity_id: "resume_patch_installed_e2e", revision: 2 }] };
  return fulfillJson(route, { revision_id: studioRevision.revision_id, accepted_patch_refs: studioRevision.accepted_patch_refs }, 201);
});
await page.route("**/api/v1/resume/render", async (route) => {
  renderRun = { render_run_id: "render_installed_e2e", resume_revision_id: studioRevision.revision_id, target_profile_id: "target_profile_installed_e2e", template_id: "resume-render-html", template_version: "1.0.0", renderer: "html_css", renderer_plugin_id: "resume-render-html-builtin", renderer_plugin_version: "1.0.0", input_sha256: "f".repeat(64), status: "completed", output_artifact_id: "artifact_render_installed_e2e", output_sha256: "1".repeat(64), output_media_type: "application/pdf", page_count: 1, preview_html: "<article><h1>平台工程实习生</h1><p>已由用户确认的本地简历预览</p></article>", checks: { pdf_generated: true }, created_by: "user", created_at: "2026-09-25T00:00:00Z" };
  return fulfillJson(route, renderRun, 201);
});
await page.route("**/api/v1/resume/render-runs/render_installed_e2e/ats-report", async (route) => fulfillJson(route, { render_run_id: "render_installed_e2e", status: "ready", page_count: 1, checks: { pdf_generated: true }, keyword_gaps: [], created_at: "2026-09-25T00:00:00Z" }));
await page.route("**/api/v1/resume/render-runs/render_installed_e2e/artifact", async (route) => route.fulfill({ status: 200, contentType: "application/pdf", body: Buffer.from("%PDF-1.4 installed-e2e") }));
await page.route("**/api/v1/resume/render-runs/render_installed_e2e/review", async (route) => fulfillJson(route, { render_run_id: "render_installed_e2e", decision: "approved", reviewer: "user", reason: "安装版人工核对通过", reviewed_at: "2026-09-25T00:00:00Z" }));
await page.route("**/api/v1/applications/application_installed_e2e/resume", async (route) => {
  application = { ...application, revision: application.revision + 1, resume_revision_id: resumeRevision.revision_id };
  return fulfillJson(route, application);
});
await page.route("**/api/v1/applications/application_installed_e2e/preparation-state", async (route) => {
  const body = JSON.parse(route.request().postData() ?? "{}");
  application = { ...application, revision: application.revision + 1, state: body.state };
  return fulfillJson(route, application);
});
await page.route("**/api/v1/applications/application_installed_e2e/submit", async (route) => {
  application = { ...application, revision: application.revision + 1, state: "submitted_by_user", submitted_at: "2026-09-25T09:00:00Z", submission_authority: "user_confirmed" };
  return fulfillJson(route, application);
});
await page.route("**/api/v1/interviews", async (route) => {
  if (route.request().method() !== "POST") return route.continue();
  const body = JSON.parse(route.request().postData() ?? "{}");
  interview = { entity_id: body.interview_id, revision: 1, application_id: application.entity_id, application_revision: application.revision, round: body.round, scheduled_at: body.scheduled_at, status: "scheduled", evidence_refs: [] };
  return fulfillJson(route, interview, 201);
});
await page.route("**/api/v1/interviews/*/reschedule", async (route) => {
  const body = JSON.parse(route.request().postData() ?? "{}");
  interview = { ...interview, revision: interview.revision + 1, scheduled_at: body.scheduled_at };
  return fulfillJson(route, interview);
});
await page.route("**/api/v1/interviews/*/complete", async (route) => {
  interview = { ...interview, revision: interview.revision + 1, status: "completed" };
  return fulfillJson(route, interview);
});
}
console.log("probe: waiting for opportunity navigation");
await page.getByRole("link", { name: "机会" }).waitFor({ state: "visible", timeout: 10000 });
await page.getByRole("link", { name: "机会" }).click();
console.log("probe: opportunity link clicked");
await page.waitForURL(/\/opportunities$/, { timeout: 10000 });
console.log(`probe: opportunity route=${page.url()}`);
console.log("probe: opportunity body=" + (await page.locator("body").innerText()).slice(0, 1200));
await page.screenshot({ path: join(artifactDir, "installed-opportunities-before-history.png"), fullPage: true });
await page.getByText("历史岗位库", { exact: true }).first().waitFor({ state: "visible", timeout: 10000 });

// Exercise the installed WebView against deterministic, locally intercepted
// response shapes. This proves the packaged UI wiring without claiming a live
// official-site fetch during the installer gate.
if (useFixture) {
await page.route("**/api/v1/jobs/official-search", async (route) => {
  await route.fulfill({
    status: 201,
    contentType: "application/json",
    body: JSON.stringify([{
      staging_id: "staging_installed_official_1",
      source_id: "official-cn-tencent-campus",
      source_ref: "https://join.qq.com/job/installed-e2e-1",
      raw_artifact_id: "artifact_installed_1",
      raw_sha256: "a".repeat(64),
      url_fingerprint: "b".repeat(64),
      content_fingerprint: "c".repeat(64),
      normalized: {
        title: "平台工程实习生",
        company: "腾讯",
        location: "深圳",
        remote: null,
        salary: null,
        requirements: ["熟悉 Python"],
        source_url: "https://join.qq.com/job/installed-e2e-1",
      },
      terms_status: "verified",
      status: "staged",
      duplicate_of: null,
      suggested_score: 0.9,
      suggested_reasons: [],
      gaps: [],
      score_breakdown: {},
      admitted_job_id: null,
      admitted_opportunity_id: null,
    }]),
  });
});
await page.route("**/api/v1/jobs/listing-lifecycle*", async (route) => {
  await route.fulfill({
    contentType: "application/json",
    body: JSON.stringify([{
      observation_id: "observation_installed_1",
      source_id: "official-cn-tencent-campus",
      query: "AI",
      source_ref: "https://join.qq.com/job/installed-e2e-1",
      url_fingerprint: "b".repeat(64),
      first_seen_at: "2026-09-25T08:00:00Z",
      last_seen_at: "2026-09-25T08:00:00Z",
      last_checked_at: "2026-09-25T09:00:00Z",
      consecutive_missing: 1,
      status: "pending_verification",
      last_success_run_id: "run_installed_1",
    }]),
  });
});
await page.route("**/api/v1/jobs/source-policies", async (route) => {
  await route.fulfill({
    contentType: "application/json",
    body: JSON.stringify([{
      source_id: "official-cn-tencent-campus",
      rate_limit_ms: 1000,
      max_retries: 2,
      failure_threshold: 3,
      failure_count: 1,
      disabled: false,
      last_error: "上次响应超时",
      updated_at: "2026-09-25T09:00:00Z",
    }]),
  });
});
await page.route("**/api/v1/jobs/official-detail", async (route) => {
  await route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      source_id: "official-cn-tencent-campus",
      source_ref: "https://join.qq.com/job/installed-e2e-1",
      captured_at: "2026-09-25T09:00:00Z",
      raw_text: JSON.stringify({ title: "平台工程实习生", description: "职位描述与任职要求" }),
      normalized: {
        title: "平台工程实习生",
        company: "腾讯",
        location: "深圳",
        remote: null,
        salary: null,
        requirements: ["熟悉 Python", "具备问题分析能力"],
        source_url: "https://join.qq.com/job/installed-e2e-1",
      },
      health: { status: "ok", message: "" },
    }),
  });
});
await page.route("**/api/v1/jobs/staging/staging_installed_official_1/admit", async (route) => {
  await route.fulfill({
    status: 201,
    contentType: "application/json",
    body: JSON.stringify({ admission: { decision: { job: { job_id: "job_installed_official_1", revision: 1 } } } }),
  });
});
await page.route("**/api/v1/jobs/job_installed_official_1/revisions/1/requirements", async (route) => {
  if (route.request().method() === "POST") {
    const body = JSON.parse(route.request().postData() ?? "{}");
    return route.fulfill({
      status: 201,
      contentType: "application/json",
      body: JSON.stringify({ requirement: { requirement_id: body.requirement_id, revision: 1, job: { job_id: "job_installed_official_1", revision: 1 }, requirement_text: body.requirement_text, importance: body.importance ?? "required", required_scopes: ["understand"], source_evidence_refs: body.source_evidence_refs ?? ["evidence_installed_official_1"], status: "proposed", capability_id: null, graph_version_id: null, review_reason: null, reviewed_at: null } }),
    });
  }
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([
      { requirement_id: "requirement_installed_official_1", revision: 1, job: { job_id: "job_installed_official_1", revision: 1 }, requirement_text: "熟悉 Python", importance: "required", required_scopes: ["understand"], source_evidence_refs: ["evidence_installed_official_1"], status: "proposed", capability_id: null, graph_version_id: null, review_reason: null, reviewed_at: null },
      { requirement_id: "requirement_installed_official_2", revision: 1, job: { job_id: "job_installed_official_1", revision: 1 }, requirement_text: "具备问题分析能力", importance: "preferred", required_scopes: ["understand"], source_evidence_refs: ["evidence_installed_official_1"], status: "proposed", capability_id: null, graph_version_id: null, review_reason: null, reviewed_at: null },
    ]),
  });
});
await page.route("**/api/v1/jobs/requirements/*/revisions/*/review", async (route) => {
  const requirementId = route.request().url().match(/requirements\/([^/]+)/)?.[1] ?? "requirement_installed_official_1";
  const body = JSON.parse(route.request().postData() ?? "{}");
  return route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ requirement: { requirement_id: requirementId, revision: 2, job: { job_id: "job_installed_official_1", revision: 1 }, requirement_text: body.final_requirement_text ?? "熟悉 Python", importance: "required", required_scopes: ["understand"], source_evidence_refs: ["evidence_installed_official_1"], status: body.decision, capability_id: body.capability_id ?? null, graph_version_id: body.graph_version_id ?? null, review_reason: body.review_reason ?? "安装版 JD 审核", reviewed_at: "2026-09-25T09:01:00Z" } }),
  });
});
await page.route("**/api/v1/capabilities/identities", async (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(["candidate_installed_e2e"]) }));
await page.route("**/api/v1/capabilities/candidate_installed_e2e", async (route) => route.fulfill({
  status: 200,
  contentType: "application/json",
  body: JSON.stringify({ candidate_id: "candidate_installed_e2e", graph_version: { graph_version_id: "graph_installed_e2e", version_label: "安装验收", parent_graph_version_id: null, change_note: "", released_at: "2026-09-25T09:00:00Z", released_by: "user", released_by_kind: "user" }, nodes: [{ capability_id: "capability_python", canonical_name: "Python", description: "", layer: "common_core", lifecycle_status: "active", graph_version_id: "graph_installed_e2e" }], relations: [], projections: [], input_revisions: [], workspace_version: "capability-workspace-v1" }),
}));
}
if (useFixture) {
  await page.reload();
  await page.waitForURL(/\/opportunities$/, { timeout: 10000 });
  await page.getByRole("button", { name: "读取官方岗位" }).click();
  const sourcePanel = page.locator("section").filter({ hasText: "国内官方校招来源" }).first();
  await sourcePanel.getByText("平台工程实习生", { exact: true }).first().waitFor();
  await sourcePanel.getByText("岗位观察：有效 0 · 待核验 1 · 已失效 0").waitFor();
  await sourcePanel.getByText("连续失败 1/3").waitFor();
  await sourcePanel.getByText("上次响应超时").waitFor();
  await sourcePanel.getByRole("button", { name: "加入并审核 JD" }).click();
  await sourcePanel.getByLabel("平台工程实习生 完整官方 JD").waitFor();
  const requirementOne = sourcePanel.getByLabel("编辑候选要求 requirement_installed_official_1");
  await requirementOne.waitFor();
  await sourcePanel.getByLabel("绑定能力 requirement_installed_official_1").selectOption("capability_python");
  await sourcePanel.getByRole("button", { name: "接受", exact: true }).first().click();
  await sourcePanel.getByRole("button", { name: "拒绝", exact: true }).click();
  await page.screenshot({ path: join(artifactDir, "installed-official-jd-review.png"), fullPage: true });
  await page.screenshot({ path: join(artifactDir, "installed-official-source-lifecycle.png"), fullPage: true });
}
else {
  console.log("probe: starting real demo loop");
  await page.getByRole("button", { name: "开始演示闭环" }).click();
  await page.getByRole("region", { name: "简历修改审核" }).waitFor({ timeout: 15000 });
  console.log("probe: real demo review rendered");
  await page.getByText(/岗位要求与来源/).waitFor({ state: "visible", timeout: 10000 });
}

if (useFixture) await page.getByRole("button", { name: "开始演示闭环" }).click();
const review = page.getByRole("region", { name: "简历修改审核" });
console.log("probe: reviewing resume patches");
await review.getByRole("button", { name: "接受", exact: true }).first().click();
await review.getByRole("button", { name: "拒绝" }).first().click();
const edited = review.locator(":scope > article").last();
await edited.getByLabel("手动编辑（用户内容）").fill("安装窗口验收中的用户确认内容");
await edited.getByRole("button", { name: "保存手动编辑并接受" }).click();
await page.screenshot({ path: join(artifactDir, "installed-resume-review-decisions.png"), fullPage: true });
await review.getByRole("button", { name: "生成目标 ResumeRevision" }).click();
await page.screenshot({ path: join(artifactDir, "installed-resume-review-generated.png"), fullPage: true });

if (useFixture) {
await page.getByRole("link", { name: "简历", exact: true }).click();
await page.getByText("高级修订工具", { exact: true }).waitFor();
const studioDisclosure = page.locator("details").filter({ hasText: "高级修订工具" });
console.log(`resume-studio disclosures=${await studioDisclosure.count()}`);
if ((await studioDisclosure.count()) !== 1) throw new Error("Expected one Resume Studio disclosure");
const studioSummary = studioDisclosure.locator("summary");
await studioSummary.scrollIntoViewIfNeeded();
if ((await studioDisclosure.getAttribute("open")) === null) await studioSummary.click({ force: true });
if ((await studioDisclosure.getAttribute("open")) === null) throw new Error("Resume Studio disclosure did not open");
const studioBase = page.locator('select[aria-label="基础简历"]');
await studioBase.focus();
await studioBase.locator(`option[value="${resumeBase.resume_id}"]`).waitFor({ state: "attached" });
await studioBase.selectOption(resumeBase.resume_id);
console.log("resume-studio base-selected");
await page.locator('input[placeholder="输入高级引用"]').fill("target_profile_installed_e2e");
await page.locator('input[placeholder="例如：平台工程师"]').fill("平台工程实习生");
const studioRevisionSelect = page.locator('select[aria-label="已审核修订"]');
await studioRevisionSelect.locator(`option[value="${resumeRevision.revision_id}"]`).waitFor({ state: "attached" });
await studioRevisionSelect.selectOption(resumeRevision.revision_id);
console.log("resume-studio revision-selected");
await page.getByRole("button", { name: "加载到本地草稿" }).click();
console.log("resume-studio draft-loaded");
const studioDraft = page.locator('textarea[aria-label="简历建议草稿"]');
console.log(`resume-studio draft-count=${await studioDraft.count()}`);
if ((await studioDraft.count()) !== 1) throw new Error("Expected one Resume Studio draft textarea");
await studioDraft.waitFor();
await studioDraft.fill(JSON.stringify({ name: "安装验收候选人", summary: "已由用户确认的平台工程实习经历" }, null, 2));
console.log("resume-studio draft-filled");
const studioEvidence = page.getByLabel("草稿证据精确引用");
console.log(`resume-studio evidence-count=${await studioEvidence.count()}`);
await studioEvidence.fill("evidence_installed_resume_1");
console.log("resume-studio evidence-filled");
const promoteButton = page.getByRole("button", { name: "审核草稿并创建新修订" });
console.log(`resume-studio promote-disabled=${await promoteButton.isDisabled()}`);
await promoteButton.click();
console.log("resume-studio promotion-clicked");
await page.waitForTimeout(500);
console.log(`resume-studio status=${(await page.locator('[role="status"]').allTextContents()).join(" | ")}`);
await page.getByText("草稿已由用户审核并生成新的不可变简历修订；现在可正式渲染。", { exact: true }).waitFor();
await page.getByRole("button", { name: "生成预览与 PDF" }).click();
await page.getByText("已由用户确认的本地简历预览", { exact: true }).waitFor();
const pdfDownload = page.waitForEvent("download");
await page.getByRole("button", { name: "下载 PDF" }).click();
const pdf = await pdfDownload;
await pdf.saveAs(join(artifactDir, "installed-resume-studio.pdf"));
await page.getByLabel("审核理由").fill("安装版人工核对通过");
await page.getByRole("button", { name: "批准" }).click();
await page.getByText(/已由用户/, { exact: false }).last().waitFor();
await page.screenshot({ path: join(artifactDir, "installed-resume-studio-render.png"), fullPage: true });

await page.getByRole("link", { name: "申请与面试" }).click();
await page.getByText("application_installed_e2e", { exact: true }).waitFor();
const applicationCard = page.locator("article.kanban-card").filter({ hasText: "application_installed_e2e" });
await applicationCard.getByLabel("选择 application_installed_e2e 的简历版本").selectOption(resumeRevision.revision_id);
await applicationCard.getByRole("button", { name: "关联简历" }).click();
await applicationCard.getByRole("button", { name: "进入待本人确认" }).click();
await applicationCard.getByRole("button", { name: "本人确认投递" }).click();
const interviewInput = applicationCard.getByLabel("填写 application_installed_e2e 的面试时间");
const localTomorrow = new Date();
localTomorrow.setDate(localTomorrow.getDate() + 1);
const pad = (value) => String(value).padStart(2, "0");
const localDateTime = `${localTomorrow.getFullYear()}-${pad(localTomorrow.getMonth() + 1)}-${pad(localTomorrow.getDate())}T10:00`;
await interviewInput.fill(localDateTime);
await applicationCard.getByRole("button", { name: "安排面试" }).click();
await page.getByText("面试轮次已安排并写入本地日历。", { exact: true }).waitFor();
await page.getByRole("button", { name: "月视图" }).click();
const downloadPromise = page.waitForEvent("download");
await page.getByRole("button", { name: "导出 .ics" }).click();
const calendarDownload = await downloadPromise;
await calendarDownload.saveAs(join(artifactDir, "installed-interviews.ics"));
if (calendarDownload.suggestedFilename() !== "guanfu-interviews.ics") throw new Error("Unexpected calendar download name");
const interviewRow = page.locator("article.calendar-list__item").first();
await page.getByRole("button", { name: "列表" }).click();
const rescheduleInput = interviewRow.getByLabel(/改期 /);
await rescheduleInput.fill(localDateTime);
await interviewRow.getByRole("button", { name: "改期" }).click();
await interviewRow.getByRole("button", { name: "完成" }).click();
await page.screenshot({ path: join(artifactDir, "installed-application-interview-calendar.png"), fullPage: true });
}
let closeResult = { invoked: false };
try {
  closeResult = await page.evaluate(() => {
    const invoke = window.__TAURI_INTERNALS__?.invoke;
    if (typeof invoke !== "function") return { invoked: false };
    void invoke("plugin:window|close", { label: "main" });
    return { invoked: true };
  });
} catch (error) {
  if (!/Target page|context.*closed|browser has been closed/i.test(String(error))) throw error;
  closeResult = { invoked: true, pageClosed: true };
}
console.log(JSON.stringify(closeResult, null, 2));
await new Promise((resolve) => setTimeout(resolve, 1500));
try { await browser.close(); } catch (error) {
  if (!/Target page|context.*closed|browser has been closed/i.test(String(error))) throw error;
}
