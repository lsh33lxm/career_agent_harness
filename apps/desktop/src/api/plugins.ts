import { apiRequest } from "./client";

export interface PluginManifest {
  id: string;
  name: string;
  version: string;
  api_version: "1";
  type: string;
  source: { repo: string; ref: string; commit: string; license: string };
  capabilities: string[];
  permissions: {
    network: string[];
    filesystem: string[];
    secrets: string[];
    external_write: boolean;
    scope: string[];
  };
  data_contracts: string[];
  healthcheck: { command: string; timeout_ms: number };
  replacement: { compatible_capabilities: string[] };
  dependencies: string[];
  core_compatibility: { min_version: string; max_version: string };
  config_schema: Record<string, unknown>;
  data_migration_version: number;
  cost_limits: { max_runtime_ms: number; max_output_bytes: number };
  security_url: string;
  terms_url: string;
  user_visible_description: string;
}

export interface PluginInstallation {
  status: string;
  enabled: boolean;
  current_version: string;
  config?: { update_policy?: "notify" | "patch_auto" | "manual" };
  last_health_status?: string | null;
}

export interface PluginCatalogItem {
  manifest: PluginManifest;
  installed: boolean;
  installation: PluginInstallation | null;
  release_scan?: {
    overall: string;
    license?: {
      status?: string;
      spdx?: string;
      repository?: string;
      ref?: string;
      commit?: string;
      commercial_restriction?: boolean;
      notice_requirement?: string;
      manual_review_status?: string;
    };
    dependencies?: {
      status?: string;
      scan_mode?: string;
      vulnerability_scan?: string;
    };
    security?: {
      status?: string;
      install_scripts_status?: string;
      network_access?: string;
    };
  };
}

export interface PluginAuditEvent {
  audit_id: string;
  plugin_id: string;
  action: string;
  actor: string;
  idempotency_key: string | null;
  payload: Record<string, unknown>;
  occurred_at: string;
}

export interface PluginAuditSummary {
  plugin_id: string;
  run_count: number;
  error_count: number;
  error_rate: number;
  latency: { average_ms: number; max_ms: number };
  provenance_hashes: string[];
  error_codes: string[];
  declared_data_scopes: string[];
  cost: { recorded_runs: number; external_cost_known: boolean };
  rollback_recommendation: Record<string, unknown>;
}

export interface PluginUninstallPreview {
  plugin_id: string;
  enabled: boolean;
  run_count: number;
  core_truth_deleted: boolean;
  artifact_bytes_deleted: boolean;
  removal_allowed: boolean;
  retained_records: string[];
}

export function listPluginAudit(pluginId: string): Promise<PluginAuditEvent[]> {
  return apiRequest(`/api/v1/plugins/${encodeURIComponent(pluginId)}/audit`);
}

export function getPluginAuditSummary(pluginId: string): Promise<PluginAuditSummary> {
  return apiRequest(`/api/v1/plugins/${encodeURIComponent(pluginId)}/audit-summary`);
}

export function previewPluginUninstall(pluginId: string): Promise<PluginUninstallPreview> {
  return apiRequest(`/api/v1/plugins/${encodeURIComponent(pluginId)}/uninstall-preview`, {
    method: "POST",
  });
}

export function setPluginUpdatePolicy(
  pluginId: string,
  policy: "notify" | "patch_auto" | "manual",
): Promise<{ plugin_id: string; update_policy: string; auto_switch: boolean }> {
  return apiRequest(`/api/v1/plugins/${encodeURIComponent(pluginId)}/update-policy`, {
    method: "POST",
    body: JSON.stringify({ policy }),
  });
}
