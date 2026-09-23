// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
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

it("only shows connected after a confirmed real connection test", async () => {
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
  expect(await screen.findAllByText("尚未配置")).toHaveLength(4);
  const keyInputs = screen.getAllByLabelText("API 密钥");
  fireEvent.change(keyInputs[0], { target: { value: "synthetic-api-key" } });
  fireEvent.click(screen.getAllByRole("button", { name: "保存配置" })[0]);
  expect(await screen.findByText(/连接测试通过前不会显示为已连接/)).toBeTruthy();
  expect(screen.getByText("尚未测试")).toBeTruthy();

  const testButton = screen.getAllByRole("button", { name: "测试连接" })[0];
  expect(testButton.hasAttribute("disabled")).toBe(true);
  fireEvent.click(screen.getAllByText("我确认执行一次外部连接请求")[0]);
  fireEvent.click(testButton);
  expect(await screen.findByText("真实连通性测试通过。")).toBeTruthy();
  await waitFor(() => expect(screen.getByText("已连接")).toBeTruthy());
  const testCall = fetcher.mock.calls.find(([url]) => String(url).endsWith("/openai/test"));
  expect(String(testCall?.[1]?.body)).toContain("confirm_external_request");
});
