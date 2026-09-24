import { apiRequest } from "./client";

export type JobStagingStatus = "staged" | "duplicate" | "admitted" | "rejected";

export interface JobStagingRecord {
  staging_id: string;
  source_id: string;
  source_ref: string;
  raw_artifact_id: string;
  raw_sha256: string;
  url_fingerprint: string;
  content_fingerprint: string;
  normalized: {
    title: string;
    company: string;
    location: string | null;
    remote: boolean | null;
    salary: string | null;
    requirements: string[];
    source_url: string | null;
  };
  terms_status: "verified" | "unknown" | "blocked";
  status: JobStagingStatus;
  duplicate_of: string | null;
  suggested_score: number;
  suggested_reasons: string[];
  gaps: string[];
  score_breakdown: Record<string, number>;
  admitted_job_id: string | null;
  admitted_opportunity_id: string | null;
}

export interface ManualJobImportRequest {
  source_ref: string;
  raw_text: string;
  query?: string;
  desired_terms?: string[];
  excluded_terms?: string[];
  preferred_locations?: string[];
  minimum_salary?: number;
}

export function listJobStaging(signal?: AbortSignal): Promise<JobStagingRecord[]> {
  return apiRequest<JobStagingRecord[]>("/api/v1/jobs/search", { signal });
}

export function importManualJob(request: ManualJobImportRequest): Promise<JobStagingRecord[]> {
  return apiRequest<JobStagingRecord[]>("/api/v1/jobs/import", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export interface OfficialSourceSearchRequest {
  source_id: "official-cn-tencent-campus" | "official-cn-meitu-campus";
  query?: string;
  desired_terms?: string[];
  excluded_terms?: string[];
  preferred_locations?: string[];
  minimum_salary?: number;
}

export function searchOfficialJobs(
  request: OfficialSourceSearchRequest,
): Promise<JobStagingRecord[]> {
  return apiRequest<JobStagingRecord[]>("/api/v1/jobs/official-search", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export interface OfficialJobDetail {
  source_id: string;
  source_ref: string;
  captured_at: string;
  raw_text: string;
  normalized: JobStagingRecord["normalized"];
  health: { status: "ok" | "blocked" | "error"; message: string };
}

export function getOfficialJobDetail(
  request: { source_id: OfficialSourceSearchRequest["source_id"]; source_ref: string },
): Promise<OfficialJobDetail> {
  return apiRequest<OfficialJobDetail>("/api/v1/jobs/official-detail", {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function admitStagedJob(stagingId: string): Promise<unknown> {
  return apiRequest(`/api/v1/jobs/staging/${encodeURIComponent(stagingId)}/admit`, {
    method: "POST",
  });
}

export interface JobSourceDocument {
  staging_id: string;
  source_id: string;
  source_ref: string;
  raw_sha256: string;
  captured_at: string;
  raw_text: string;
}

export function getJobSourceDocument(stagingId: string): Promise<JobSourceDocument> {
  return apiRequest<JobSourceDocument>(
    `/api/v1/jobs/staging/${encodeURIComponent(stagingId)}/source-document`,
  );
}

export interface JobRequirement {
  requirement_id: string;
  revision: number;
  job: { job_id: string; revision: number };
  requirement_text: string;
  importance: "required" | "preferred";
  required_scopes: string[];
  source_evidence_refs: string[];
  status: "proposed" | "accepted" | "rejected" | "superseded";
  capability_id: string | null;
  graph_version_id: string | null;
  review_reason: string | null;
  reviewed_at: string | null;
}

export interface JobRequirementProposal {
  requirement_id: string;
  requirement_text: string;
  importance?: "required" | "preferred";
  source_evidence_refs: string[];
}

export function listJobRequirements(
  jobId: string,
  jobRevision: number,
): Promise<JobRequirement[]> {
  return apiRequest<JobRequirement[]>(
    `/api/v1/jobs/${encodeURIComponent(jobId)}/revisions/${jobRevision}/requirements`,
  );
}

export function proposeJobRequirement(
  jobId: string,
  jobRevision: number,
  request: JobRequirementProposal,
): Promise<{ requirement: JobRequirement }> {
  return apiRequest(`/api/v1/jobs/${encodeURIComponent(jobId)}/revisions/${jobRevision}/requirements`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}

export function reviewJobRequirement(
  requirementId: string,
  revision: number,
  request: {
    decision: "accepted" | "rejected" | "superseded";
    review_reason: string;
    final_requirement_text?: string;
    capability_id?: string;
    graph_version_id?: string;
  },
): Promise<{ requirement: JobRequirement }> {
  return apiRequest(`/api/v1/jobs/requirements/${encodeURIComponent(requirementId)}/revisions/${revision}/review`, {
    method: "POST",
    body: JSON.stringify(request),
  });
}
