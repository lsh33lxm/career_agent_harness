export interface HealthResponse {
  status: "ok";
  service: string;
  version: string;
  environment: string;
}

export type PriorityLevel = "low" | "medium" | "high" | "urgent";

export interface OpportunitySummary {
  opportunity: {
    entity_id: string;
    revision: number;
    schema_version: number;
    state: "discovered" | "watching" | "qualified" | "preparing" | "declined" | "expired" | "archived";
  };
  job: {
    job_id: string;
    revision: number;
  };
  suggested_priority: {
    opportunity_id: string;
    level: PriorityLevel;
    reasons: string[];
    input_revisions: Array<{ entity_id: string; revision: number }>;
    calculated_at: string;
    score: number | null;
    rank: number | null;
  } | null;
  user_priority: {
    opportunity_id: string;
    level: PriorityLevel;
    actor: "user";
    set_at: string;
    reason: string | null;
  } | null;
}

export interface CommandCommitResult {
  entity_id: string;
  revision: number;
  revision_id: string;
  event_id: string;
}

export interface ManualAdmissionRequest {
  command_id: string;
  job_id: string;
  job_revision: number;
  reason?: string;
}

export interface ProposalAdmissionRequest extends ManualAdmissionRequest {
  proposal_id: string;
  proposal_reason: string;
  proposed_by: "agent" | "rule";
}

export interface UserPriorityRequest {
  command_id: string;
  expected_revision: number;
  level: PriorityLevel;
  reason?: string;
}

export interface OpportunityAdmissionCommit {
  admission: {
    opportunity: OpportunitySummary["opportunity"] | null;
  };
  commit: CommandCommitResult;
}

interface RuntimeConfig {
  apiBaseUrl: string;
  launchToken: string;
  demoMode: boolean;
}

import { isVisualReviewMode, visualReviewRequest } from "./visualReview";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status?: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

function runtimeConfig(): RuntimeConfig {
  const injected = window.__ACH_CONFIG__;
  const configuredBaseUrl =
    injected?.apiBaseUrl ?? import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8765";
  const launchToken = injected?.launchToken ?? import.meta.env.VITE_LAUNCH_TOKEN;
  const demoMode = injected?.demoMode === true || import.meta.env.VITE_DEMO_MODE === "true";

  if (!launchToken && !demoMode) {
    throw new ApiError("本地服务尚未启动，请先启动职业核心；演示模式可离线查看界面");
  }
  let parsedBaseUrl: URL;
  try {
    parsedBaseUrl = new URL(configuredBaseUrl);
  } catch {
    throw new ApiError("Local API must use an explicit 127.0.0.1 address");
  }
  if (
    parsedBaseUrl.protocol !== "http:"
    || parsedBaseUrl.hostname !== "127.0.0.1"
    || !parsedBaseUrl.port
    || parsedBaseUrl.username
    || parsedBaseUrl.password
    || parsedBaseUrl.pathname !== "/"
  ) {
    throw new ApiError("Local API must use an explicit 127.0.0.1 address");
  }
  return { apiBaseUrl: parsedBaseUrl.origin, launchToken: launchToken ?? "", demoMode };
}

export async function apiRequest<T>(
  path: string,
  init: RequestInit = {},
  idempotencyKey?: string,
): Promise<T> {
  // 仅开发环境的视觉验收模式：fixture 直出，不触网（生产构建中此分支被移除）。
  if (import.meta.env.DEV && isVisualReviewMode()) {
    return visualReviewRequest(path, init) as Promise<T>;
  }
  const config = runtimeConfig();
  if (config.demoMode && !config.launchToken) {
    throw new ApiError("当前是离线演示模式，本地职业核心尚未连接");
  }
  let response: Response;
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${config.launchToken}`);
  if (init.body !== undefined) {
    headers.set("Content-Type", "application/json");
  }
  if (idempotencyKey !== undefined) {
    headers.set("X-Idempotency-Key", idempotencyKey);
  }

  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("Local API is unavailable");
  }

  if (!response.ok) {
    let detail: unknown;
    try {
      detail = (await response.json() as { detail?: unknown }).detail;
    } catch {
      detail = undefined;
    }
    const safeDetail = typeof detail === "string"
      ? detail.replaceAll(config.launchToken, "[redacted]")
      : undefined;
    throw new ApiError(safeDetail ?? `Local API request failed (${response.status})`, response.status);
  }
  return (await response.json()) as T;
}

export async function apiRequestBlob(path: string, init: RequestInit = {}): Promise<Blob> {
  if (import.meta.env.DEV && isVisualReviewMode()) {
    throw new ApiError("视觉验收模式不提供文件下载");
  }
  const config = runtimeConfig();
  if (config.demoMode && !config.launchToken) {
    throw new ApiError("当前是离线演示模式，本地职业核心尚未连接");
  }
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${config.launchToken}`);
  let response: Response;
  try {
    response = await fetch(`${config.apiBaseUrl}${path}`, { ...init, headers });
  } catch {
    throw new ApiError("Local API is unavailable");
  }
  if (!response.ok) {
    throw new ApiError(`Local API request failed (${response.status})`, response.status);
  }
  return response.blob();
}

export function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  return apiRequest<HealthResponse>("/health", { signal });
}

export function listOpportunities(signal?: AbortSignal): Promise<OpportunitySummary[]> {
  return apiRequest<OpportunitySummary[]>("/api/v1/opportunities", { signal });
}

export function getOpportunity(
  opportunityId: string,
  signal?: AbortSignal,
): Promise<OpportunitySummary> {
  return apiRequest<OpportunitySummary>(
    `/api/v1/opportunities/${encodeURIComponent(opportunityId)}`,
    { signal },
  );
}

export function admitOpportunityManually(
  request: ManualAdmissionRequest,
  idempotencyKey: string,
): Promise<OpportunityAdmissionCommit> {
  return apiRequest<OpportunityAdmissionCommit>(
    "/api/v1/opportunities/manual-admissions",
    { method: "POST", body: JSON.stringify(request) },
    idempotencyKey,
  );
}

export function admitOpportunityProposal(
  request: ProposalAdmissionRequest,
  idempotencyKey: string,
): Promise<OpportunityAdmissionCommit> {
  return apiRequest<OpportunityAdmissionCommit>(
    "/api/v1/opportunities/proposal-admissions",
    { method: "POST", body: JSON.stringify(request) },
    idempotencyKey,
  );
}

export function setOpportunityUserPriority(
  opportunityId: string,
  request: UserPriorityRequest,
  idempotencyKey: string,
): Promise<CommandCommitResult> {
  return apiRequest<CommandCommitResult>(
    `/api/v1/opportunities/${encodeURIComponent(opportunityId)}/user-priority`,
    { method: "PATCH", body: JSON.stringify(request) },
    idempotencyKey,
  );
}
