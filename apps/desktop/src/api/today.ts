// Typed client for the Core Today read model (contract 0.8.0, D-018).
// Today is a deterministic Core projection: this client only fetches it, and
// the UI renders the returned order and reasons without re-ranking.
import { apiRequest, type PriorityLevel } from "./client";

export type TodayItemKind =
  | "opportunity_action"
  | "application_step"
  | "interview_prep"
  | "enhancement_task"
  | "review_request";

export type TodayReasonCode =
  | "user_priority_urgent"
  | "user_priority_high"
  | "user_priority_medium"
  | "user_priority_low"
  | "suggested_priority_urgent"
  | "suggested_priority_high"
  | "suggested_priority_medium"
  | "suggested_priority_low"
  | "missing_user_priority"
  | "missing_suggested_priority"
  | "deadline_approaching"
  | "interview_upcoming"
  | "opportunity_active"
  | "application_step_pending"
  | "interview_prep_due"
  | "gap_linked_task"
  | "pending_user_review";

export interface TodaySourceRef {
  entity_id: string;
  kind: string;
  revision: number;
}

export interface TodayReason {
  code: TodayReasonCode;
  explanation: string;
}

export interface TodayItem {
  item_id: string;
  kind: TodayItemKind;
  source_refs: TodaySourceRef[];
  reasons: TodayReason[];
  user_priority: PriorityLevel | null;
  suggested_priority: PriorityLevel | null;
  deadline_at: string | null;
  interview_at: string | null;
}

export interface TodayQueue {
  items: TodayItem[];
  /** Exact input revisions used to compute the queue; kept for staleness display. */
  input_revisions: TodaySourceRef[];
  generated_at: string;
  policy_version: string;
}

export function getToday(signal?: AbortSignal): Promise<TodayQueue> {
  return apiRequest<TodayQueue>("/api/v1/today", { signal });
}
