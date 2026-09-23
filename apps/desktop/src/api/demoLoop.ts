import { apiRequest } from "./client";

export interface DemoLoopResult {
  staging_id: string;
  opportunity_id: string;
  application_id: string;
  application_state: string;
  patch_id: string | null;
  resume_revision_id: string;
  interview_id: string | null;
  interview_revision: number | null;
  interview_prep_proposal_id: string | null;
  interview_feedback_proposal_id: string | null;
}

export function runDemoFullLoop(): Promise<DemoLoopResult> {
  return apiRequest<DemoLoopResult>("/api/v1/career-loop/demo-full", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function startDemoLoop(): Promise<DemoLoopResult> {
  return apiRequest<DemoLoopResult>("/api/v1/career-loop/demo-start", {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function approveDemoResume(
  patchId: string,
  applicationId: string,
  decision: "accepted" | "rejected",
  editedValue?: unknown,
): Promise<{ patch_id: string; review_status: string; reviewed_at: string | null; review_source: string; review_note: string; evidence_ids: string[] }> {
  return apiRequest("/api/v1/career-loop/demo-approve-resume", {
    method: "POST",
    body: JSON.stringify({ patch_id: patchId, application_id: applicationId, decision, edited_value: editedValue }),
  });
}

export function createDemoResumeRevision(applicationId: string): Promise<{ resume_revision_id: string; application_id: string }> {
  return apiRequest("/api/v1/career-loop/demo-resume-revision", {
    method: "POST", body: JSON.stringify({ application_id: applicationId }),
  });
}
