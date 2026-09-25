import { apiRequest } from "./client";

export type ProviderKind = "openai" | "anthropic" | "deepseek" | "openai_compatible";

export interface ModelProviderConfig {
  provider_id: string;
  provider_kind: ProviderKind;
  base_url: string;
  default_model: string;
  timeout_seconds: number;
  has_api_key: boolean;
  masked_api_key: string | null;
  connection_status: "unconfigured" | "not_tested" | "connected" | "failed";
  last_checked_at: string | null;
  last_error_code: string | null;
  revision: number;
}

export interface ModelProviderInput {
  provider_id: string;
  provider_kind: ProviderKind;
  base_url: string;
  default_model: string;
  timeout_seconds: number;
  api_key?: string;
}

export const listModelProviders = () => apiRequest<ModelProviderConfig[]>("/api/v1/model-providers");
export const configureModelProvider = (input: ModelProviderInput) => apiRequest<ModelProviderConfig>(
  "/api/v1/model-providers/configure",
  { method: "POST", body: JSON.stringify(input) },
);
export const testModelProvider = (providerId: string) => apiRequest<ModelProviderConfig & { test: { success: boolean } }>(
  `/api/v1/model-providers/${encodeURIComponent(providerId)}/test`,
  { method: "POST", body: JSON.stringify({ confirm_external_request: true }) },
);
