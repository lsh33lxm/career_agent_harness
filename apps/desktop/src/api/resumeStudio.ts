import { apiRequest, apiRequestBlob } from "./client";

export interface ResumeTargetProfile {
  target_profile_id: string;
  resume_id: string;
  title: string;
  company: string | null;
  opportunity_id: string | null;
  opportunity_revision: number | null;
  requirement_refs: Array<{ entity_id: string; revision: number }>;
  keyword_gaps: string[];
  status: string;
  created_by: string;
  created_at: string;
}

export interface ResumeRenderRun {
  render_run_id: string;
  resume_revision_id: string;
  target_profile_id: string | null;
  template_id: string;
  template_version: string;
  renderer: string;
  renderer_plugin_id: string;
  renderer_plugin_version: string;
  input_sha256: string;
  status: string;
  output_artifact_id: string;
  output_sha256: string;
  output_media_type: string;
  page_count: number;
  preview_html: string;
  checks: Record<string, boolean>;
  created_by: string;
  created_at: string;
}

export interface ResumeTemplate {
  template_id: string;
  name: string;
  version: string;
  renderer: string;
  content_sha256: string;
  description: string;
  status: "active" | "disabled";
  created_at: string;
}

export interface ResumeRenderReview {
  render_run_id: string;
  decision: "approved" | "rejected";
  reviewer: string;
  reason: string;
  reviewed_at: string;
}

export interface ResumePatch {
  patch_id: string;
  revision: number;
  status: "proposed" | "accepted" | "rejected";
}

export interface ResumeRevisionResult {
  revision_id: string;
  accepted_patch_refs: Array<{ entity_id: string; revision: number }>;
}

export interface ResumeAtsReport {
  render_run_id: string;
  status: string;
  page_count: number;
  checks: Record<string, boolean>;
  keyword_gaps: string[];
  created_at: string;
}

export interface ResumeStudioDiff {
  resume_id: string;
  base_revision: number;
  resume_revision_id: string;
  diff: string;
  claim_provenance: Array<{ entity_id: string; revision: number }>;
  evidence_provenance: string[];
}

export interface ResumeValidationResult {
  valid: boolean;
  data: Record<string, unknown> | null;
  warnings: string[];
  errors: string[];
}

export function validateResumeContent(content: Record<string, unknown>): Promise<ResumeValidationResult> {
  return apiRequest("/api/v1/resume/validate", {
    method: "POST", body: JSON.stringify({ content }),
  });
}

export function createTargetProfile(input: {
  target_profile_id: string;
  resume_id: string;
  title: string;
  company?: string;
}): Promise<ResumeTargetProfile> {
  return apiRequest("/api/v1/resume/target-profiles", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function renderResume(input: {
  resume_revision_id: string;
  target_profile_id?: string;
  template_id?: string;
}): Promise<ResumeRenderRun> {
  return apiRequest("/api/v1/resume/render", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function listResumeTemplates(): Promise<ResumeTemplate[]> {
  return apiRequest("/api/v1/resume/templates");
}

export function reviewResumeRender(
  renderRunId: string,
  input: { decision: "approved" | "rejected"; reason: string },
): Promise<ResumeRenderReview> {
  return apiRequest(
    `/api/v1/resume/render-runs/${encodeURIComponent(renderRunId)}/review`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function proposeResumePatch(
  input: Record<string, unknown>,
  idempotencyKey: string,
): Promise<ResumePatch> {
  return apiRequest(
    "/api/v1/resume/patch-proposals",
    { method: "POST", body: JSON.stringify(input) },
    idempotencyKey,
  );
}

export function reviewResumePatch(
  patchId: string,
  input: Record<string, unknown>,
  idempotencyKey: string,
): Promise<ResumePatch> {
  return apiRequest(
    `/api/v1/resume/patches/${encodeURIComponent(patchId)}/review`,
    { method: "POST", body: JSON.stringify(input) },
    idempotencyKey,
  );
}

export function createResumeRevision(
  input: Record<string, unknown>,
  idempotencyKey: string,
): Promise<ResumeRevisionResult> {
  return apiRequest(
    "/api/v1/resume/revisions",
    { method: "POST", body: JSON.stringify(input) },
    idempotencyKey,
  );
}

export function restoreResumeRevision(
  input: { command_id: string; resume_id: string; revision_id: string; expected_base_revision: number },
  idempotencyKey: string,
): Promise<Record<string, unknown>> {
  return apiRequest(
    "/api/v1/resume/restore",
    { method: "POST", body: JSON.stringify(input) },
    idempotencyKey,
  );
}

export function restoreResumeBaseRevision(
  input: {
    command_id: string;
    resume_id: string;
    source_base_revision: number;
    expected_base_revision: number;
  },
  idempotencyKey: string,
): Promise<Record<string, unknown>> {
  return apiRequest(
    "/api/v1/resume/base-restore",
    { method: "POST", body: JSON.stringify(input) },
    idempotencyKey,
  );
}

export function getResumeDiff(revisionId: string): Promise<ResumeStudioDiff> {
  return apiRequest(`/api/v1/resume/diff/${encodeURIComponent(revisionId)}`);
}

export function getAtsReport(renderRunId: string): Promise<ResumeAtsReport> {
  return apiRequest(`/api/v1/resume/render-runs/${encodeURIComponent(renderRunId)}/ats-report`);
}

export function downloadRenderArtifact(renderRunId: string): Promise<Blob> {
  return apiRequestBlob(
    `/api/v1/resume/render-runs/${encodeURIComponent(renderRunId)}/artifact`,
  );
}
