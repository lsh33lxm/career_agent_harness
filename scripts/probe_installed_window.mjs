import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";
import { join } from "node:path";

const port = process.env.CDP_PORT ?? "9231";
const artifactDir = process.env.INSTALLED_WINDOW_ARTIFACT_DIR ?? "artifacts/verification/installed-window-e2e-current";
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
await page.getByRole("link", { name: "机会" }).click();

// Exercise the installed WebView against deterministic, locally intercepted
// response shapes. This proves the packaged UI wiring without claiming a live
// official-site fetch during the installer gate.
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
await page.getByRole("button", { name: "读取官方岗位" }).click();
const sourcePanel = page.getByRole("region", { name: "国内官方校招来源" });
await sourcePanel.getByText("平台工程实习生").waitFor();
await sourcePanel.getByText("岗位观察：有效 0 · 待核验 1 · 已失效 0").waitFor();
await sourcePanel.getByText("连续失败 1/3").waitFor();
await sourcePanel.getByText("上次响应超时").waitFor();
await page.screenshot({ path: join(artifactDir, "installed-official-source-lifecycle.png"), fullPage: true });

await page.getByRole("button", { name: "开始演示闭环" }).click();
const review = page.getByRole("region", { name: "简历修改审核" });
await review.getByRole("button", { name: "接受", exact: true }).first().click();
await review.getByRole("button", { name: "拒绝" }).first().click();
const edited = review.locator(":scope > article").last();
await edited.getByLabel("手动编辑（用户内容）").fill("安装窗口验收中的用户确认内容");
await edited.getByRole("button", { name: "保存手动编辑并接受" }).click();
await page.screenshot({ path: join(artifactDir, "installed-resume-review-decisions.png"), fullPage: true });
await review.getByRole("button", { name: "生成目标 ResumeRevision" }).click();
await page.screenshot({ path: join(artifactDir, "installed-resume-review-generated.png"), fullPage: true });
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
