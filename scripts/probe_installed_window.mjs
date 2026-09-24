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
