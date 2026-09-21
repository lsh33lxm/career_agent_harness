// Typed client for the Core Capability Workspace read model (contract 0.13.0, D-023).
import { apiRequest } from "./client";

export type CapabilityLayer = "common_core" | "track" | "opportunity_specific";
export type MarketScope = "target" | "broad";

export interface CapabilityGraphVersion {
  graph_version_id: string;
  version_label: string;
  parent_graph_version_id: string | null;
  change_note: string;
  released_at: string;
  released_by: string;
  released_by_kind: "user" | "rule";
}

export interface CapabilityNode {
  capability_id: string;
  canonical_name: string;
  description: string;
  layer: CapabilityLayer;
  lifecycle_status: "active" | "deprecated" | "retired";
  graph_version_id: string;
}

export interface CapabilityRelation {
  relation_id: string;
  source_capability_id: string;
  target_capability_id: string;
  relation_type: "prerequisite" | "part_of" | "related_to";
  graph_version_id: string;
}

export interface PersonalCapabilityState {
  personal_state_id: string;
  candidate_id: string;
  capability_id: string;
  understand: boolean;
  explain: boolean;
  apply: boolean;
  evidence: boolean;
  interview_ready: boolean;
  revision: number;
  display_status: "unknown" | "understood" | "practiced" | "applied" | "verified" | "resume_ready";
  updated_at: string;
}

export interface EvidenceBinding {
  binding_id: string;
  evidence_ref_id: string | null;
  project_evidence_id: string | null;
  project_evidence_revision: number | null;
  authority: "code_verified" | "document_supported" | "user_confirmed" | "ai_inferred";
  scopes: string[];
}

export interface MarketBinding {
  binding_id: string;
  market_scope: MarketScope;
  source_evidence_refs: string[];
  opportunity_id: string | null;
  job_requirement_id: string | null;
}

export interface InvestmentState {
  investment_state_id: string;
  recommendation: "low" | "medium" | "high";
  score: number;
  reasons: string[];
  rule_version: string;
  calculated_at: string;
}

export interface CapabilityProjection {
  capability_id: string;
  personal_state: PersonalCapabilityState | null;
  evidence_bindings: EvidenceBinding[];
  target_market_bindings: MarketBinding[];
  broad_market_bindings: MarketBinding[];
  investment_state: InvestmentState | null;
}

export interface WorkspaceInputRef {
  kind: string;
  entity_id: string;
  revision: number | null;
}

export interface CapabilityWorkspace {
  candidate_id: string;
  graph_version: CapabilityGraphVersion | null;
  nodes: CapabilityNode[];
  relations: CapabilityRelation[];
  projections: CapabilityProjection[];
  input_revisions: WorkspaceInputRef[];
  workspace_version: "capability-workspace-v1";
}

export function getCapabilities(
  candidateId: string,
  graphVersionId?: string,
  signal?: AbortSignal,
): Promise<CapabilityWorkspace> {
  const query = graphVersionId
    ? `?graph_version_id=${encodeURIComponent(graphVersionId)}`
    : "";
  return apiRequest<CapabilityWorkspace>(
    `/api/v1/capabilities/${encodeURIComponent(candidateId)}${query}`,
    { signal },
  );
}

export function listCapabilityIdentities(signal?: AbortSignal): Promise<string[]> {
  return apiRequest<string[]>("/api/v1/capabilities/identities", { signal });
}
