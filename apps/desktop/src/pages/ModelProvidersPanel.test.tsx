// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { ModelProvidersPanel } from "./ModelProvidersPanel";

const response = (body: unknown) => new Response(JSON.stringify(body), {
  status: 200,
  headers: { "Content-Type": "application/json" },
});

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  delete window.__ACH_CONFIG__;
});

it("预设自动填充端点与模型，用户只输入 API Key；连接通过后才显示已连接", async () => {
  window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "provider-ui-token" };
  let configured = false;
  let connected = false;
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/api/v1/model-providers") && (init?.method ?? "GET") === "GET") {
      return response(configured ? [{
        provider_id: "openai", provider_kind: "openai", base_url: "https://api.openai.com/v1",
        default_model: "gpt-4.1-mini", timeout_seconds: 30, has_api_key: true,
        masked_api_key: "••••••••", connection_status: connected ? "connected" : "not_tested",
        last_checked_at: null, last_error_code: null, revision: 1,
      }] : []);
    }
    if (url.endsWith("/configure")) { configured = true; return response({}); }
    if (url.endsWith("/openai/test")) {
      connected = true;
      return response({ test: { success: true }, connection_status: "connected" });
    }
    throw new Error(`unexpected request ${url}`);
  });
  vi.stubGlobal("fetch", fetcher);

  render(<ModelProvidersPanel />);

  // 预设卡片可搜索，OpenAI 预设打开抽屉后自动填充端点与推荐模型
  expect(await screen.findByText("尚未配置模型服务。从下方“可添加厂商”选择一个预设，只需填入 API Key。")).toBeTruthy();
  fireEvent.click(screen.getByRole("tab", { name: "添加厂商" }));
  fireEvent.click(await screen.findByRole("button", { name: /^OpenAI OpenAI 协议/ }));
  const dialog = await screen.findByRole("dialog", { name: "添加 OpenAI" });
  expect((within(dialog).getByLabelText("服务地址") as HTMLInputElement).value).toBe("https://api.openai.com/v1");
  expect((within(dialog).getByLabelText("默认模型") as HTMLSelectElement).value).toBe("gpt-4.1-mini");

  // API Key 是唯一必填项；保存前测试不可用
  fireEvent.change(screen.getByLabelText("API 密钥"), { target: { value: "synthetic-api-key" } });
  fireEvent.click(screen.getByRole("button", { name: "保存配置" }));
  await waitFor(() => expect(configured).toBe(true));
  const configureCall = fetcher.mock.calls.find(([url]) => String(url).endsWith("/configure"));
  expect(String(configureCall?.[1]?.body)).toContain('"provider_id":"openai"');
  expect(String(configureCall?.[1]?.body)).toContain('"base_url":"https://api.openai.com/v1"');
  expect(String(configureCall?.[1]?.body)).toContain('"default_model":"gpt-4.1-mini"');
  expect(await screen.findByText(/连接测试通过前不会显示为已连接/)).toBeTruthy();
  expect(await screen.findByText("尚未测试")).toBeTruthy();

  // 明确确认后才能发起真实连接测试
  fireEvent.click(screen.getAllByRole("button", { name: "测试连接" })[0]);
  const editDialog = await screen.findByRole("dialog", { name: "编辑 OpenAI" });
  const testButton = within(editDialog).getByRole("button", { name: "测试连接" });
  expect((testButton as HTMLButtonElement).disabled).toBe(true);
  fireEvent.click(within(editDialog).getByText("我确认执行一次外部连接请求"));
  fireEvent.click(testButton);
  expect(await screen.findByText("真实连通性测试通过。")).toBeTruthy();
  await waitFor(() => expect(screen.getByText("已连接")).toBeTruthy());
  const testCall = fetcher.mock.calls.find(([url]) => String(url).endsWith("/openai/test"));
  expect(String(testCall?.[1]?.body)).toContain("confirm_external_request");
});

it("本地模型与自定义厂商分组可见且可搜索", async () => {
  window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "provider-ui-token" };
  vi.stubGlobal("fetch", vi.fn(async () => response([])));

  render(<ModelProvidersPanel />);
  expect(await screen.findByRole("tab", { name: "本地模型" })).toBeTruthy();
  expect(screen.getByRole("tab", { name: "高级配置" })).toBeTruthy();

  fireEvent.click(screen.getByRole("tab", { name: "添加厂商" }));
  fireEvent.change(await screen.findByLabelText("搜索厂商预设"), { target: { value: "gemini" } });
  expect(screen.getByText("Google Gemini")).toBeTruthy();
  expect(screen.queryByText("Ollama")).toBeNull();

  fireEvent.change(screen.getByLabelText("搜索厂商预设"), { target: { value: "" } });
  fireEvent.click(screen.getByRole("tab", { name: "本地模型" }));
  expect(screen.getByText("Ollama")).toBeTruthy();
  expect(screen.getByText("LM Studio")).toBeTruthy();
});
