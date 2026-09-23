import { apiRequest } from "./client";

export type MemoryType = "profile" | "preference" | "fact" | "task" | "interest";

export interface MemoryRevision {
  memory_id: string;
  revision: number;
  memory_type: MemoryType;
  scope_kind: "user" | "workspace" | "session";
  scope_id: string;
  status: "confirmed" | "tombstoned";
  content: string;
  source_type: string;
  source_locator: string;
  source_refs: string[];
  confidence: number;
  created_by: string;
  confirmed_by: string;
  created_at: string;
}

export interface MemoryProposal {
  proposal_id: string;
  memory_type: MemoryType;
  content: string;
  source_locator: string;
  confidence: number;
  created_by: string;
  status: "pending" | "approved" | "rejected";
}

export interface MemorySearchResult {
  memory: MemoryRevision;
  relevance: number;
}

export function listMemories(signal?: AbortSignal): Promise<MemorySearchResult[]> {
  return apiRequest<MemorySearchResult[]>("/api/v1/memory", { signal });
}

export function listMemoryProposals(signal?: AbortSignal): Promise<MemoryProposal[]> {
  return apiRequest<MemoryProposal[]>("/api/v1/memory/proposals", { signal });
}

export function createMemoryProposal(memoryType: MemoryType, content: string): Promise<MemoryProposal> {
  return apiRequest<MemoryProposal>("/api/v1/memory/proposals", {
    method: "POST",
    body: JSON.stringify({ memory_type: memoryType, content }),
  });
}

export function reviewMemoryProposal(
  proposalId: string,
  decision: "approved" | "rejected",
  editedContent?: string,
): Promise<MemoryProposal> {
  return apiRequest<MemoryProposal>(`/api/v1/memory/proposals/${encodeURIComponent(proposalId)}/review`, {
    method: "POST",
    body: JSON.stringify({
      decision,
      reason: decision === "approved" ? "用户确认" : "用户拒绝",
      edited_content: editedContent,
    }),
  });
}

export function deleteMemory(memoryId: string): Promise<MemoryRevision> {
  return apiRequest<MemoryRevision>(`/api/v1/memory/${encodeURIComponent(memoryId)}/delete`, {
    method: "POST", body: JSON.stringify({ reason: "用户从工作台删除" }),
  });
}
