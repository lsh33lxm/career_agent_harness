// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { PluginsPage } from "./PluginsPage";

const response = (body: unknown) => new Response(JSON.stringify(body), {
  status: 200,
  headers: { "Content-Type": "application/json" },
});

const catalog = [{
  manifest: {
    id: "echo-fixture", name: "Echo Fixture", version: "1.0.0", api_version: "1",
    type: "worker_plugin",
    source: { repo: "builtin://echo-fixture", ref: "v1", commit: "builtin-echo-v1", license: "Apache-2.0" },
    capabilities: ["fixture.echo", "health"],
    permissions: { network: [], filesystem: [], secrets: [], external_write: false, scope: ["read_models"] },
    data_contracts: ["PluginEnvelope"], healthcheck: { command: "health", timeout_ms: 5000 },
    replacement: { compatible_capabilities: ["fixture.echo"] }, dependencies: [],
    core_compatibility: { min_version: "0.1.0", max_version: "0.x" }, config_schema: {},
    data_migration_version: 0, cost_limits: { max_runtime_ms: 5000, max_output_bytes: 1000000 },
    security_url: "about:blank", terms_url: "about:blank",
    user_visible_description: "Offline echo fixture",
  },
  installed: true,
  installation: {
    status: "enabled", enabled: true, current_version: "1.0.0",
    config: { update_policy: "notify" }, last_health_status: "ok",
  },
  release_scan: {
    overall: "passed",
    license: {
      status: "verified", spdx: "Apache-2.0", repository: "builtin://echo-fixture",
      ref: "v1", commit: "builtin-echo-v1", notice_requirement: "not_applicable",
      manual_review_status: "not_required",
    },
    dependencies: { status: "verified", scan_mode: "declared_license_only" },
    security: { status: "offline_pass", network_access: "none" },
  },
}];

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  delete window.__ACH_CONFIG__;
});

it("shows manifest details, policy, audit and uninstall impact without external writes", async () => {
  window.__ACH_CONFIG__ = { apiBaseUrl: "http://127.0.0.1:8765", launchToken: "plugins-ui-token" };
  const fetcher = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    if (url.endsWith("/api/v1/plugins") && (init?.method ?? "GET") === "GET") return response(catalog);
    if (url.endsWith("/api/v1/model-providers") && (init?.method ?? "GET") === "GET") return response([]);
    if (url.includes("/api/v1/tasks?limit=100") && (init?.method ?? "GET") === "GET") return response([]);
    if (url.endsWith("/audit")) return response([{ audit_id: "audit_1", plugin_id: "echo-fixture", action: "install", actor: "user", idempotency_key: null, payload: {}, occurred_at: "now" }]);
    if (url.endsWith("/audit-summary")) return response({
      plugin_id: "echo-fixture", run_count: 2, error_count: 0, error_rate: 0,
      latency: { average_ms: 1, max_ms: 2 }, provenance_hashes: ["a".repeat(64)],
      error_codes: [], declared_data_scopes: ["scope:read_models"],
      cost: { recorded_runs: 2, external_cost_known: false },
      rollback_recommendation: { action: "retain", automatic: false },
    });
    if (url.endsWith("/uninstall-preview")) return response({
      plugin_id: "echo-fixture", enabled: false, run_count: 2,
      core_truth_deleted: false, artifact_bytes_deleted: false, removal_allowed: true,
      retained_records: ["plugin_runs", "plugin_audit_events", "artifacts"],
    });
    if (url.endsWith("/update-policy")) return response({ plugin_id: "echo-fixture", update_policy: "manual", auto_switch: false });
    throw new Error(`unexpected request ${url}`);
  });
  vi.stubGlobal("fetch", fetcher);

  render(<PluginsPage />);
  expect(await screen.findByRole("heading", { name: "本地连通性检查" })).toBeTruthy();
  fireEvent.click(screen.getByText("查看详情与权限"));
  expect(screen.getByText("builtin://echo-fixture")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("Echo Fixture更新策略"), { target: { value: "manual" } });
  await waitFor(() => expect(screen.getByRole("status").textContent).toContain("更新策略已设为 手动批准"));
  fireEvent.click(screen.getByRole("button", { name: "审计" }));
  expect(await screen.findByRole("region", { name: "Echo Fixture审计" })).toBeTruthy();
  expect(screen.getByText(/运行 2 次/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "卸载影响" }));
  expect(await screen.findByRole("region", { name: "Echo Fixture卸载影响" })).toBeTruthy();
  expect(fetcher.mock.calls.some(([url]) => String(url).endsWith("/audit-summary"))).toBe(true);
});
