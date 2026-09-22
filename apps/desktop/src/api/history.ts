import { apiRequest } from "./client";

export type ApplicationState = "preparing" | "ready_for_review" | "submitted_by_user"
  | "screen" | "oa" | "interview" | "offer" | "rejected" | "withdrawn" | "closed";

export interface ApplicationRead {
  entity_id: string;
  revision: number;
  opportunity_id: string;
  opportunity_revision: number;
  state: ApplicationState;
  resume_revision_id: string | null;
  submission_authority: "user_confirmed" | "portal_receipt" | null;
  submission_evidence_ref_id: string | null;
  submitted_at: string | null;
}

export interface OutcomeRead {
  entity_id: string;
  revision: number;
  application_id: string;
  application_revision: number;
  result: "offer" | "rejection" | "withdrawal" | "closed";
  occurred_at: string;
  authority: "user_confirmed" | "portal_receipt";
  evidence_refs: string[];
  recorded_by: string;
}

export interface InterviewRead {
  entity_id: string;
  revision: number;
  application_id: string;
  application_revision: number;
  round: "screen" | "technical" | "loop" | "offer_talk";
  scheduled_at: string;
  status: "scheduled" | "completed" | "cancelled";
  evidence_refs: string[];
}

export function listApplications(signal?: AbortSignal): Promise<ApplicationRead[]> {
  return apiRequest<ApplicationRead[]>("/api/v1/applications", { signal });
}

export function listOutcomes(applicationId: string, signal?: AbortSignal): Promise<OutcomeRead[]> {
  return apiRequest<OutcomeRead[]>(
    `/api/v1/applications/${encodeURIComponent(applicationId)}/outcomes`, { signal },
  );
}

export function listInterviews(applicationId: string, signal?: AbortSignal): Promise<InterviewRead[]> {
  return apiRequest<InterviewRead[]>(
    `/api/v1/applications/${encodeURIComponent(applicationId)}/interviews`, { signal },
  );
}

export function createInterviewPrepProposal(
  interviewId: string, input: { mode: "technical" | "behavioral"; focus: string },
): Promise<{ proposal_id: string }> {
  return apiRequest<{ proposal_id: string }>(
    `/api/v1/interviews/${encodeURIComponent(interviewId)}/prep-proposals`,
    { method: "POST", body: JSON.stringify(input) },
  );
}
