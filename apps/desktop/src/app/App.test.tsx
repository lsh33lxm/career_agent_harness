// @vitest-environment jsdom
import { render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { App } from "./App";

afterEach(() => {
  vi.unstubAllGlobals();
  window.__ACH_CONFIG__ = undefined;
});

it("renders the complete P0 application navigation", () => {
  window.__ACH_CONFIG__ = {
    apiBaseUrl: "http://127.0.0.1:8765",
    launchToken: "ephemeral-test-token",
  };
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));

  render(<App />);

  for (const label of [
    "今天",
    "机会",
    "项目",
    "能力",
    "简历",
    "历史",
    "我的",
    "设置",
  ]) {
    expect(screen.getByRole("link", { name: label })).toBeTruthy();
  }
});
