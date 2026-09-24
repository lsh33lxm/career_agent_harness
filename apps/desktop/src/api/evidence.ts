import { apiRequest } from "./client";

export interface EvidenceProvenance {
  evidence_ref: { evidence_ref_id: string; snapshot_id: string; artifact_id: string; selector: string | null };
  snapshot: { snapshot_id: string; source_id: string; captured_at: string; artifact_id: string };
  source: { source_id: string; source_type: string; locator: string };
  artifact: { artifact_id: string; sha256: string; media_type: string; artifact_class: "public_source" | "personal" | "sensitive"; byte_length: number };
}
export interface EvidencePageRead {
  items: EvidenceProvenance[];
  next_cursor: string | null;
}
export function listEvidence(after: string | null, signal?: AbortSignal): Promise<EvidencePageRead> {
  const query = new URLSearchParams({ limit: "25" });
  if (after !== null) query.set("after", after);
  return apiRequest<EvidencePageRead>(`/api/v1/evidence?${query}`, { signal });
}
export function getEvidence(refId: string, signal?: AbortSignal): Promise<EvidenceProvenance> {
  return apiRequest<EvidenceProvenance>(`/api/v1/evidence/${encodeURIComponent(refId)}`, { signal });
}
