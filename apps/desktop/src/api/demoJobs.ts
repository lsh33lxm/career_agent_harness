import demoData from "../../../../data/demo/jobs.json";

import type { LegacyJobSummary } from "./legacy";

export function listDemoJobs(): LegacyJobSummary[] {
  return demoData.map((job, index) => ({
    staging_id: job.demo_id,
    title: job.title,
    company: job.company,
    location: job.location,
    salary: null,
    source_url: null,
    status: "staged",
    duplicate_of: null,
    suggested_score: Math.max(60, 94 - index),
    review_status: "historical_unconfirmed",
    source_path: "演示数据包 / 历史岗位摘要",
    source_class: "demo_historical_sample",
    source_sha256: "demo-only",
    row_number: index + 1,
    imported_at: "2026-09-16T00:00:00Z",
    tags: job.skills,
  }));
}

export function getDemoJob(stagingId: string): LegacyJobSummary | null {
  return listDemoJobs().find((job) => job.staging_id === stagingId) ?? null;
}
