import { apiRequest } from "./client";

export interface DemoStoryStep {
  key: string;
  label: string;
  status: string;
  entity_id?: string | null;
}

export interface DemoStoryLink {
  kind: string;
  id: string;
  label: string;
}

export interface DemoStoryEvent {
  event_id: string;
  event_type: string;
  label: string;
  entity_id: string;
  revision: number;
  occurred_at: string;
}

export interface DemoStoryRequirement {
  requirement_id: string;
  requirement_text: string;
  status: string;
}

export interface DemoStory {
  available: boolean;
  message?: string;
  staging_id?: string | null;
  application_id?: string;
  opportunity_id?: string | null;
  resume_revision_id?: string | null;
  evidence_ref_id?: string | null;
  score?: number | null;
  gaps?: string[];
  requirements?: DemoStoryRequirement[];
  steps: DemoStoryStep[];
  events: DemoStoryEvent[];
  links: DemoStoryLink[];
}

export function getDemoStory(signal?: AbortSignal): Promise<DemoStory> {
  return apiRequest<DemoStory>("/api/v1/career-loop/demo-story", { signal });
}
