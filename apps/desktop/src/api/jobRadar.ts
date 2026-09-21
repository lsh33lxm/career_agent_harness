import { apiRequest } from "./client";

export type JobStagingStatus = "staged" | "duplicate" | "admitted" | "rejected";

export interface JobStagingRecord {
  staging_id: string;
  source_id: string;
  source_ref: string;
  raw_artifact_id: string;
  raw_sha256: string;
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

export function admitStagedJob(stagingId: string): Promise<unknown> {
  return apiRequest(`/api/v1/jobs/staging/${encodeURIComponent(stagingId)}/admit`, {
    method: "POST",
  });
}
