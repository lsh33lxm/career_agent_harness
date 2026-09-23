import { apiRequest } from "./client";

export interface DemoLoopResult {
  staging_id: string;
  opportunity_id: string;
  application_id: string;
  application_state: string;
  interview_id: string;
  interview_revision: number;
  interview_prep_proposal_id: string;
  interview_feedback_proposal_id: string;
}

export function runDemoFullLoop(): Promise<DemoLoopResult> {
  return apiRequest<DemoLoopResult>("/api/v1/career-loop/demo-full", {
    method: "POST",
    body: JSON.stringify({}),
  });
}
