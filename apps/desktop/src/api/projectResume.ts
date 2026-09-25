import { apiRequest } from "./client";
export interface ProjectRead {
  project: { project_id: string; revision: number; display_name: string; created_at: string; created_by: string };
  evidence: Array<{ evidence_id: string; project_id: string; revision: number; summary: string; authority: string; review_status: string; freshness: string; source_manifest: { manifest_id: string; scan_scope_id: string; scan_scope_revision: number; entries: Array<{ relative_path: string; sha256: string; byte_length: number }> } }>;
  evidence_basis: string;
}
export interface ResumeBaseRead { resume_id: string; revision: number; candidate_id: string; sections: Record<string, unknown>; created_at: string; created_by: string }
export interface ResumeRevisionRead { revision_id: string; resume_id: string; base_revision: number; content: Record<string, unknown>; content_sha256: string; accepted_patch_refs: Array<{ entity_id: string; revision: number }>; created_at: string; created_by: string }
export function listProjects(signal?: AbortSignal): Promise<ProjectRead["project"][]> {
  return apiRequest("/api/v1/projects", { signal });
}
export function getProject(id: string, revision: string, signal?: AbortSignal): Promise<ProjectRead> {
  return apiRequest(`/api/v1/projects/${encodeURIComponent(id)}${revision ? `?revision=${encodeURIComponent(revision)}` : ""}`, { signal });
}
export function listResumeBases(signal?: AbortSignal): Promise<ResumeBaseRead[]> {
  return apiRequest("/api/v1/resumes", { signal });
}
export function getResumeBase(id: string, revision: string, signal?: AbortSignal): Promise<ResumeBaseRead> {
  return apiRequest(`/api/v1/resumes/${encodeURIComponent(id)}/base${revision ? `?revision=${encodeURIComponent(revision)}` : ""}`, { signal });
}
export function getResumeRevision(id: string, signal?: AbortSignal): Promise<ResumeRevisionRead> {
  return apiRequest(`/api/v1/resume-revisions/${encodeURIComponent(id)}`, { signal });
}
export function listResumeBaseRevisions(id: string, signal?: AbortSignal): Promise<ResumeBaseRead[]> {
  return apiRequest(`/api/v1/resumes/${encodeURIComponent(id)}/bases`, { signal });
}
export function listResumeRevisions(id: string, signal?: AbortSignal): Promise<ResumeRevisionRead[]> {
  return apiRequest(`/api/v1/resumes/${encodeURIComponent(id)}/revisions`, { signal });
}

export function saveResumeBase(
  input: { command_id: string; resume_id: string; candidate_id: string; sections: Record<string, unknown> },
  idempotencyKey: string,
): Promise<ResumeBaseRead> {
  return apiRequest("/api/v1/resumes/bases", {
    method: "POST", body: JSON.stringify(input),
  }, idempotencyKey);
}
