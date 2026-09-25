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

export function createApplication(input: {
  command_id: string;
  application_id: string;
  opportunity_id: string;
  opportunity_revision: number;
}): Promise<ApplicationRead> {
  return apiRequest<ApplicationRead>("/api/v1/applications", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function attachResumeToApplication(applicationId: string, input: { command_id: string; expected_revision: number; resume_revision_id: string }): Promise<ApplicationRead> {
  return apiRequest<ApplicationRead>(`/api/v1/applications/${encodeURIComponent(applicationId)}/resume`, { method: "POST", body: JSON.stringify(input) });
}

export function setApplicationPreparationState(applicationId: string, input: { command_id: string; expected_revision: number; state: "preparing" | "ready_for_review" }): Promise<ApplicationRead> {
  return apiRequest<ApplicationRead>(`/api/v1/applications/${encodeURIComponent(applicationId)}/preparation-state`, { method: "POST", body: JSON.stringify(input) });
}

export function advanceApplicationState(applicationId: string, input: { command_id: string; expected_revision: number; state: Exclude<ApplicationState, "preparing" | "ready_for_review"> }): Promise<ApplicationRead> {
  return apiRequest<ApplicationRead>(`/api/v1/applications/${encodeURIComponent(applicationId)}/state`, { method: "POST", body: JSON.stringify(input) });
}

export function submitApplication(applicationId: string, input: { command_id: string; expected_revision: number; resume_revision_id: string }): Promise<ApplicationRead> {
  return apiRequest<ApplicationRead>(`/api/v1/applications/${encodeURIComponent(applicationId)}/submit`, { method: "POST", body: JSON.stringify(input) });
}

export function scheduleInterview(input: { command_id: string; interview_id: string; application_id: string; application_revision: number; round: InterviewRead["round"]; scheduled_at: string }): Promise<InterviewRead> {
  return apiRequest<InterviewRead>("/api/v1/interviews", { method: "POST", body: JSON.stringify(input) });
}

export function completeInterview(interviewId: string, input: { command_id: string; expected_revision: number }): Promise<InterviewRead> {
  return apiRequest<InterviewRead>(`/api/v1/interviews/${encodeURIComponent(interviewId)}/complete`, { method: "POST", body: JSON.stringify(input) });
}

export function cancelInterview(interviewId: string, input: { command_id: string; expected_revision: number }): Promise<InterviewRead> {
  return apiRequest<InterviewRead>(`/api/v1/interviews/${encodeURIComponent(interviewId)}/cancel`, { method: "POST", body: JSON.stringify(input) });
}

export function rescheduleInterview(interviewId: string, input: { command_id: string; expected_revision: number; scheduled_at: string }): Promise<InterviewRead> {
  return apiRequest<InterviewRead>(`/api/v1/interviews/${encodeURIComponent(interviewId)}/reschedule`, { method: "POST", body: JSON.stringify(input) });
}

export interface InterviewProposalRead {
  proposal_id: string;
  target_knowledge_id: string | null;
  base_revision: number | null;
  category: string;
  title: string;
  proposed_content: string;
  evidence_refs: string[];
  status: "pending" | "approved" | "rejected" | "withdrawn";
  review_reason?: string | null;
}

export function createInterviewPrepProposal(
  interviewId: string,
  input: { mode: "technical" | "behavioral"; focus: string },
): Promise<InterviewProposalRead> {
  return apiRequest<InterviewProposalRead>(
    `/api/v1/interviews/${encodeURIComponent(interviewId)}/prep-proposals`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function createInterviewFeedbackProposal(
  interviewId: string,
  input: { question: string; answer: string },
): Promise<InterviewProposalRead> {
  return apiRequest<InterviewProposalRead>(
    `/api/v1/interviews/${encodeURIComponent(interviewId)}/feedback-proposals`,
    { method: "POST", body: JSON.stringify(input) },
  );
}

export function createInterviewLearningPlanProposal(
  interviewId: string,
  gaps: string[],
): Promise<InterviewProposalRead> {
  return apiRequest<InterviewProposalRead>(
    `/api/v1/interviews/${encodeURIComponent(interviewId)}/learning-plan-proposals`,
    { method: "POST", body: JSON.stringify({ gaps }) },
  );
}

export function reviewInterviewProposal(
  proposalId: string,
  decision: "approved" | "rejected",
  reason: string,
): Promise<InterviewProposalRead> {
  return apiRequest<InterviewProposalRead>(
    `/api/v1/knowledge/proposals/${encodeURIComponent(proposalId)}/review`,
    { method: "POST", body: JSON.stringify({ decision, reviewer: "user", reason }) },
  );
}

export function createOfferPreparationProposal(applicationId: string): Promise<{ proposal_id: string }> {
  return apiRequest<{ proposal_id: string }>(
    `/api/v1/outcome-insights/applications/${encodeURIComponent(applicationId)}/offer-preparation`,
    { method: "POST" },
  );
}

export function createRejectionPatternProposal(): Promise<{ proposal_id: string }> {
  return apiRequest<{ proposal_id: string }>(
    "/api/v1/outcome-insights/rejection-pattern",
    { method: "POST" },
  );
}
