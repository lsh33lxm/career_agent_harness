import { apiRequest, type CommandCommitResult } from "./client";

export interface InboxCandidate {
  candidate_node_id: string;
  proposed_canonical_name: string;
  proposed_description: string;
  proposed_layer: string;
  source_evidence_refs: string[];
  discovered_by: string;
  status: "pending" | "accepted" | "ignored" | "merged";
  reviewed_by: string | null;
  reviewed_by_kind: string | null;
  review_reason: string | null;
  merge_target_capability_id: string | null;
}
export interface InboxItem { candidate: InboxCandidate; revision: number }
export interface InboxReviewRequest {
  command_id: string;
  expected_revision: number;
  decision: "accept" | "reject";
  reason: string;
}
export interface InboxReceipt {
  candidate: InboxCandidate;
  commit: CommandCommitResult;
  capability_id: string | null;
  graph_version: { graph_version_id: string } | null;
}
export function listCapabilityInbox(signal?: AbortSignal): Promise<InboxItem[]> {
  return apiRequest("/api/v1/capability-inbox", { signal });
}
export function getCapabilityInboxItem(id: string): Promise<InboxItem> {
  return apiRequest(`/api/v1/capability-inbox/${encodeURIComponent(id)}`);
}
export function reviewCapabilityCandidate(id: string, request: InboxReviewRequest, key: string): Promise<InboxReceipt> {
  return apiRequest(`/api/v1/capability-inbox/${encodeURIComponent(id)}/review`,
    { method: "POST", body: JSON.stringify(request) }, key);
}
