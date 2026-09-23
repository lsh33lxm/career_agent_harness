import { apiRequest } from "./client";

export type CommunicationStatus =
  | "pending_review" | "approved" | "rejected" | "sent" | "replied" | "follow_up" | "closed" | "blocked";

export interface CommunicationDraft {
  draft_id: string;
  opportunity_id: string;
  source_staging_id: string | null;
  channel: "email" | "platform_message" | "follow_up_note";
  recipient: string | null;
  body: string;
  status: CommunicationStatus;
  provenance: Record<string, string>;
  reviewed_by: string | null;
  review_reason: string | null;
}

export interface CommunicationSummary {
  daily_limit: number;
  created_today: number;
  remaining_today: number;
  counts: Record<string, number>;
  channel_counts: Record<string, number>;
  reply_count: number;
  follow_up_count: number;
}

export function listCommunicationDrafts(): Promise<CommunicationDraft[]> {
  return apiRequest<CommunicationDraft[]>("/api/v1/communications/drafts");
}

export function getCommunicationSummary(): Promise<CommunicationSummary> {
  return apiRequest<CommunicationSummary>("/api/v1/communications/summary");
}

export function createCommunicationDraft(input: {
  draft_id: string; opportunity_id: string; source_staging_id?: string;
  channel: CommunicationDraft["channel"]; recipient?: string; body: string;
  provenance?: Record<string, string>;
}): Promise<CommunicationDraft> {
  return apiRequest<CommunicationDraft>("/api/v1/communications/drafts", {
    method: "POST", body: JSON.stringify(input),
  });
}

export function reviewCommunicationDraft(
  draftId: string, decision: "approved" | "rejected", reason: string,
): Promise<CommunicationDraft> {
  return apiRequest<CommunicationDraft>(`/api/v1/communications/drafts/${encodeURIComponent(draftId)}/review`, {
    method: "POST", body: JSON.stringify({ decision, reason }),
  });
}

export function transitionCommunicationDraft(draftId: string, status: CommunicationStatus): Promise<CommunicationDraft> {
  return apiRequest<CommunicationDraft>(`/api/v1/communications/drafts/${encodeURIComponent(draftId)}/transition`, {
    method: "POST", body: JSON.stringify({ status }),
  });
}
