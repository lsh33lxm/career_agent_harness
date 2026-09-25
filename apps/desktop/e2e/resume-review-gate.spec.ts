import { expect, test, type Page } from "@playwright/test";
import { mkdir, writeFile, readFile } from "node:fs/promises";
import { join } from "node:path";

const webPort = process.env.ACH_VERIFY_WEB_PORT ?? "5174";
const apiPort = process.env.ACH_VERIFY_API_PORT ?? "8784";
const apiBase = `http://127.0.0.1:${apiPort}`;
const artifactDir = process.env.ACH_VERIFY_ARTIFACT_DIR ?? "../../artifacts/verification/playwright-output";
const statePath = join(artifactDir, "resume-review-state.json");

async function prepareDemoPage(page: Page) {
  await page.addInitScript(({ baseUrl }) => {
    window.__ACH_CONFIG__ = { apiBaseUrl: baseUrl, launchToken: "", demoMode: true };
  }, { baseUrl: apiBase });
  const externalRequests: string[] = [];
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === "127.0.0.1" || url.hostname === "localhost") {
      await route.continue();
    } else {
      externalRequests.push(url.origin);
      await route.abort("internetdisconnected");
    }
  });
  return externalRequests;
}

async function verifyLayout(page: Page, width: number, artifactName: string) {
  await page.setViewportSize({ width, height: 900 });
  await page.waitForTimeout(250);
  const metrics = await page.evaluate(() => {
    const sidebar = document.querySelector<HTMLElement>(".sidebar")!.getBoundingClientRect();
    const workspace = document.querySelector<HTMLElement>(".workspace")!.getBoundingClientRect();
    return {
      viewport: window.innerWidth,
      document: document.documentElement.scrollWidth,
      sidebarRight: sidebar.right,
      workspaceLeft: workspace.left,
      workspaceRight: workspace.right,
    };
  });
  expect(metrics.document).toBeLessThanOrEqual(metrics.viewport + 1);
  expect(metrics.sidebarRight).toBeLessThanOrEqual(metrics.workspaceLeft + 1);
  expect(metrics.workspaceRight).toBeLessThanOrEqual(metrics.viewport + 1);
  await page.screenshot({ path: join(artifactDir, artifactName), fullPage: true });
}

test("Resume Review Gate full UI flow persists through refresh", async ({ page, request }) => {
  await mkdir(artifactDir, { recursive: true });
  const externalRequests = await prepareDemoPage(page);
  const startedAt = Date.now();
  await page.goto("/opportunities");
  await expect(page.getByText("演示模式 · 仅展示脱敏样例，不连接真实模型或外部平台")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Agent可观测研发工程师" })).toBeVisible();
  expect(Date.now() - startedAt).toBeLessThan(30_000);
  await page.getByRole("button", { name: "查看详情" }).first().click();
  const detail = page.getByRole("complementary", { name: "岗位详情" });
  await expect(detail).toContainText("演示数据包未公开完整 JD");
  await page.screenshot({ path: join(artifactDir, "01-demo-job-detail.png"), fullPage: true });
  await detail.getByRole("button", { name: "关闭岗位详情" }).click();

  await page.getByRole("button", { name: "开始演示闭环" }).click();
  const review = page.getByRole("region", { name: "简历修改审核" });
  await expect(review).toBeVisible();
  await expect(review).toContainText("本地演示 / 待人工审核");
  await expect(review).toContainText("JD 要求");
  await expect(review).toContainText("岗位 Evidence");
  const patchCards = review.locator(":scope > article");
  await expect(patchCards).toHaveCount(3);
  await page.screenshot({ path: join(artifactDir, "02-patches-before-review.png"), fullPage: true });

  const acceptedCard = patchCards.nth(0);
  const rejectedCard = patchCards.nth(1);
  const editedCard = patchCards.nth(2);
  const acceptedPatchId = (await acceptedCard.locator("h4").innerText()).match(/Patch (\S+)/)?.[1];
  const rejectedPatchId = (await rejectedCard.locator("h4").innerText()).match(/Patch (\S+)/)?.[1];
  const editedPatchId = (await editedCard.locator("h4").innerText()).match(/Patch (\S+)/)?.[1];
  expect(acceptedPatchId && rejectedPatchId && editedPatchId).toBeTruthy();
  expect(await review.getByRole("button", { name: "生成目标 ResumeRevision" }).count()).toBe(0);

  await acceptedCard.getByRole("button", { name: "接受", exact: true }).click();
  await expect(acceptedCard).toContainText("已接受");
  await expect(review.getByRole("button", { name: "生成目标 ResumeRevision" })).toHaveCount(0);
  await rejectedCard.getByRole("button", { name: "拒绝" }).click();
  await expect(rejectedCard).toContainText("已拒绝");
  await editedCard.getByLabel("手动编辑（用户内容）").fill("用户核验后的演示经历，不代表真实个人事实");
  await editedCard.getByRole("button", { name: "保存手动编辑并接受" }).click();
  await expect(editedCard).toContainText("用户手动编辑");
  await expect(editedCard).toContainText("已接受");
  const generateButton = review.getByRole("button", { name: "生成目标 ResumeRevision" });
  await expect(generateButton).toBeVisible();
  await page.screenshot({ path: join(artifactDir, "03-patch-decisions.png"), fullPage: true });

  await generateButton.click();
  const generated = review.getByText(/已生成版本：/);
  await expect(generated).toBeVisible();
  await expect(generated).toContainText("状态仍为准备中");
  const storyResponse = await request.get(`${apiBase}/api/v1/career-loop/demo-story`);
  expect(storyResponse.ok()).toBeTruthy();
  const story = await storyResponse.json();
  const revisionId = story.resume_revision_id as string;
  const applicationId = story.application_id as string;
  expect(revisionId).toBeTruthy();
  expect(applicationId).toBeTruthy();

  const revisionResponse = await request.get(`${apiBase}/api/v1/resume-revisions/${revisionId}`);
  expect(revisionResponse.ok()).toBeTruthy();
  const revision = await revisionResponse.json();
  const acceptedRefs = (revision.accepted_patch_refs as Array<{ entity_id: string }>).map((ref) => ref.entity_id);
  expect(acceptedRefs).toContain(acceptedPatchId);
  expect(acceptedRefs).toContain(editedPatchId);
  expect(acceptedRefs).not.toContain(rejectedPatchId);
  expect(JSON.stringify(revision.content)).toContain("用户核验后的演示经历，不代表真实个人事实");
  const baseResponse = await request.get(`${apiBase}/api/v1/resumes/${revision.resume_id}/base?revision=${revision.base_revision}`);
  expect(baseResponse.ok()).toBeTruthy();
  const base = await baseResponse.json();
  expect(JSON.stringify(base.sections)).not.toContain("用户核验后的演示经历，不代表真实个人事实");

  const applicationResponse = await request.get(`${apiBase}/api/v1/applications/${applicationId}`);
  expect(applicationResponse.ok()).toBeTruthy();
  const application = await applicationResponse.json();
  expect(application.resume_revision_id).toBe(revisionId);
  expect(application.state).toBe("preparing");
  expect(application.submitted_at).toBeNull();
  await page.screenshot({ path: join(artifactDir, "04-revision-and-application.png"), fullPage: true });

  await page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "历史" }).click();
  const historyStory = page.getByRole("region", { name: "演示闭环" });
  await expect(historyStory).toContainText(revisionId);
  await expect(historyStory).toContainText(applicationId);
  await expect(historyStory).toContainText("用户手动编辑");
  await expect(page.getByText("当前阶段：准备中")).toBeVisible();
  await page.screenshot({ path: join(artifactDir, "05-history-trace.png"), fullPage: true });

  await page.getByRole("navigation", { name: "主导航" }).getByRole("link", { name: "知识" }).click();
  const knowledgeStory = page.getByRole("region", { name: "演示闭环追溯" });
  await expect(knowledgeStory).toContainText(acceptedPatchId!);
  await expect(knowledgeStory).toContainText(rejectedPatchId!);
  await expect(knowledgeStory).toContainText(editedPatchId!);
  await expect(knowledgeStory).toContainText(revisionId);
  await expect(knowledgeStory).toContainText(applicationId);
  await page.screenshot({ path: join(artifactDir, "06-knowledge-trace.png"), fullPage: true });

  await page.reload();
  await expect(page.getByRole("region", { name: "演示闭环追溯" })).toContainText(revisionId);
  await expect(page.getByRole("region", { name: "演示闭环追溯" })).toContainText(applicationId);
  for (const [width, name] of [[1280, "07-layout-1280.png"], [1440, "08-layout-1440.png"], [720, "09-layout-720.png"]] as const) {
    await verifyLayout(page, width, name);
  }
  await page.keyboard.press("Tab");
  const focusStyle = await page.evaluate(() => {
    const active = document.activeElement;
    return active ? getComputedStyle(active).outlineStyle : "none";
  });
  expect(focusStyle).not.toBe("none");
  await expect.poll(() => Date.now() - startedAt).toBeLessThan(30_000);
  expect(externalRequests).toEqual([]);
  await writeFile(statePath, JSON.stringify({
    opportunity_id: story.opportunity_id,
    application_id: applicationId,
    resume_revision_id: revisionId,
    accepted_patch_ids: acceptedRefs,
    rejected_patch_id: rejectedPatchId,
    edited_patch_id: editedPatchId,
    external_requests: externalRequests,
  }, null, 2));
});

test("API restart preserves the reviewed revision in History and Knowledge", async ({ page }) => {
  const ids = JSON.parse(await readFile(statePath, "utf8")) as {
    application_id: string;
    resume_revision_id: string;
    rejected_patch_id: string;
    edited_patch_id: string;
  };
  await prepareDemoPage(page);
  await page.goto("/history");
  const story = page.getByRole("region", { name: "演示闭环" });
  await expect(story).toContainText(ids.resume_revision_id);
  await expect(story).toContainText(ids.application_id);
  await expect(story).toContainText(ids.rejected_patch_id);
  await expect(story).toContainText(ids.edited_patch_id);
  await expect(page.getByText("当前阶段：准备中")).toBeVisible();
  await page.reload();
  await expect(page.getByRole("region", { name: "演示闭环" })).toContainText(ids.resume_revision_id);
  await page.screenshot({ path: join(artifactDir, "10-after-api-restart.png"), fullPage: true });
});

test("API unavailable keeps Demo Mode usable and reports Chinese recovery text", async ({ page }) => {
  await page.addInitScript(() => {
    window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:1", launchToken: "", demoMode: true };
  });
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname === "127.0.0.1" || url.hostname === "localhost") await route.continue();
    else await route.abort("internetdisconnected");
  });
  await page.goto("/opportunities");
  await expect(page.getByText("演示模式 · 仅展示脱敏样例，不连接真实模型或外部平台")).toBeVisible();
  await expect(page.getByRole("alert").filter({ hasText: "本地职业核心尚未连接" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Agent可观测研发工程师" })).toBeVisible();
  await page.screenshot({ path: join(artifactDir, "11-api-unavailable-demo-browser.png"), fullPage: true });
  await page.getByRole("button", { name: "开始演示闭环" }).click();
  await expect(page.getByRole("status").filter({ hasText: "本地职业核心暂不可用" })).toBeVisible();
  await page.screenshot({ path: join(artifactDir, "12-api-unavailable-review-action.png"), fullPage: true });
  const body = await page.locator("body").innerText();
  expect(body).not.toContain("Local API");
  expect(body).not.toContain("launch token");
});
