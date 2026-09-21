import { apiRequest } from "./client";

export interface LegacyImportFileReport {
  relative_path: string;
  source_class: string;
  read_count: number;
  new_count: number;
  updated_count: number;
  unchanged_count: number;
  duplicate_count: number;
  failed_count: number;
  failures: string[];
}

export interface LegacyImportReport {
  batch_id: string;
  source_root: string;
  source_signature_before: string;
  source_signature_after: string;
  status: "completed" | "failed";
  started_at: string;
  finished_at: string;
  files: LegacyImportFileReport[];
  totals: Record<string, number>;
  importer_version: string;
}

export interface LegacyImportStatus {
  configured_source_root: string | null;
  source_accessible: boolean;
  latest_report: LegacyImportReport | null;
}

export interface LegacyJobSummary {
  staging_id: string;
  title: string;
  company: string;
  location: string | null;
  salary: string | null;
  source_url: string | null;
  status: "staged" | "duplicate" | "admitted" | "rejected";
  duplicate_of: string | null;
  suggested_score: number;
  review_status: "historical_unconfirmed" | "needs_review" | "duplicate";
  source_path: string;
  source_class: string;
  source_sha256: string;
  row_number: number;
  imported_at: string;
  tags: string[];
}

export interface LegacyJobDetail {
  job: LegacyJobSummary;
  jd_text: string;
  raw_record: Record<string, unknown>;
  transform: Record<string, unknown>;
  batch_id: string;
  related_interviews: Record<string, unknown>[];
}

export function getLegacyImportStatus(signal?: AbortSignal): Promise<LegacyImportStatus> {
  return apiRequest<LegacyImportStatus>("/api/v1/legacy/status", { signal });
}

export function runLegacyImport(sourceRoot?: string): Promise<LegacyImportReport> {
  return apiRequest<LegacyImportReport>("/api/v1/legacy/import", {
    method: "POST",
    body: JSON.stringify(sourceRoot ? { source_root: sourceRoot } : {}),
  });
}

export function listLegacyJobs(
  filters: {
    query?: string;
    company?: string;
    location?: string;
    status?: string;
    limit?: number;
  } = {},
  signal?: AbortSignal,
): Promise<LegacyJobSummary[]> {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const suffix = params.size ? `?${params.toString()}` : "";
  return apiRequest<LegacyJobSummary[]>(`/api/v1/legacy/jobs${suffix}`, { signal });
}

export function getLegacyJob(stagingId: string, signal?: AbortSignal): Promise<LegacyJobDetail> {
  return apiRequest<LegacyJobDetail>(
    `/api/v1/legacy/jobs/${encodeURIComponent(stagingId)}`,
    { signal },
  );
}
