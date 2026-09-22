export interface KnowledgeCitation {
  knowledge_id: string;
  revision: number;
  evidence_refs: string[];
  source_type: string;
  source_locator: string;
  authority: string;
}

export interface KnowledgeSearchResult {
  knowledge_id: string;
  revision: number;
  title: string;
  snippet: string;
  score: number;
  lexical_score: number;
  semantic_score: number;
  search_mode: "lexical" | "hybrid";
  category: string;
  status: string;
  citation: KnowledgeCitation;
}

export interface KnowledgeSearchPage {
  items: KnowledgeSearchResult[];
  query: string;
  evidence_sufficient: boolean;
  message: string | null;
  next_cursor: string | null;
}

export interface WikiHealthIssue {
  code: string;
  severity: "warning" | "error";
  knowledge_id: string;
  detail: string;
}

export interface WikiHealthReport {
  score: number;
  page_count: number;
  link_count: number;
  issues: WikiHealthIssue[];
}

export function getWikiHealth(signal?: AbortSignal): Promise<WikiHealthReport> {
  return apiRequest<WikiHealthReport>("/api/v1/wiki/health", { signal });
}

export interface KnowledgeRevision {
  knowledge_id: string;
  revision: number;
  title: string;
  content: string;
  evidence_refs: string[];
  category?: string;
}

export interface KnowledgeProposal {
  proposal_id: string;
  target_knowledge_id: string | null;
  base_revision: number | null;
  category: string;
  title: string;
  proposed_content: string;
  status: "pending" | "approved" | "rejected" | "withdrawn";
}

export interface KnowledgeProposalInput {
  category: string;
  title: string;
  content: string;
  evidence_refs: string[];
  target_knowledge_id: string;
  base_revision: number;
}

export interface WikiOperationProposal {
  operation_id: string;
  target_knowledge_id: string;
  operation: "move" | "rename" | "archive";
  new_title: string | null;
  new_slug: string | null;
  parent_knowledge_id: string | null;
  status: "pending" | "approved" | "rejected";
}

export interface WikiOperationInput {
  operation: "move" | "rename" | "archive";
  requested_by: string;
  new_title?: string;
  new_slug?: string;
  parent_knowledge_id?: string;
}

export const getWikiRevisions = (knowledgeId: string) =>
  apiRequest<KnowledgeRevision[]>(`/api/v1/wiki/pages/${encodeURIComponent(knowledgeId)}/revisions`);

export const createKnowledgeProposal = (input: KnowledgeProposalInput) =>
  apiRequest<KnowledgeProposal>("/api/v1/knowledge/proposals", {
    method: "POST",
    body: JSON.stringify({ ...input, authority: "document_supported", created_by: "USER" }),
  });

export const reviewKnowledgeProposal = (
  proposalId: string,
  decision: "approved" | "rejected",
  reason: string,
) => apiRequest<KnowledgeProposal>(
  `/api/v1/knowledge/proposals/${encodeURIComponent(proposalId)}/review`,
  { method: "POST", body: JSON.stringify({ decision, reviewer: "user", reason }) },
);

export const createWikiOperation = (knowledgeId: string, input: WikiOperationInput) =>
  apiRequest<WikiOperationProposal>(
    `/api/v1/wiki/pages/${encodeURIComponent(knowledgeId)}/operations`,
    { method: "POST", body: JSON.stringify(input) },
  );

export const reviewWikiOperation = (
  operationId: string,
  decision: "approved" | "rejected",
  reason: string,
) => apiRequest<WikiOperationProposal>(
  `/api/v1/wiki/operations/${encodeURIComponent(operationId)}/review`,
  { method: "POST", body: JSON.stringify({ decision, reviewer: "用户", reason }) },
);
import { apiRequest } from "./client";
