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

export interface DemoStory {
  available: boolean;
  message?: string;
  application_id?: string;
  opportunity_id?: string | null;
  resume_revision_id?: string | null;
  steps: DemoStoryStep[];
  events: DemoStoryEvent[];
  links: DemoStoryLink[];
}

export function getDemoStory(signal?: AbortSignal): Promise<DemoStory> {
  return apiRequest<DemoStory>("/api/v1/career-loop/demo-story", { signal });
}
