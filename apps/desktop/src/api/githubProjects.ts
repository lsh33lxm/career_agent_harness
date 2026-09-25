import { apiRequest } from "./client";

export interface GitHubAnalysis {
  analysis_id: string;
  project_id: string;
  repository_url: string;
  commit_sha: string;
  fetched_at: string;
  file_count: number;
  byte_count: number;
  readme_sha256: string | null;
  profile: {
    summary: string;
    directory_structure: string[];
    dependency_manifests: string[];
    key_modules: string[];
    technology_stack: string[];
    tests: string[];
    deployment: string[];
    recent_activity: Array<{ commit_sha: string; authored_at: string; author: string; title: string }>;
    outcome_clues: string[];
    risk_notes: string[];
  };
  provenance: { readme: string | null; analyzed_files: string[]; analyzer: string };
}

export const analyzeGitHubProject = (repositoryUrl: string, usePrivateToken: boolean) => apiRequest<GitHubAnalysis>(
  "/api/v1/github/analyze",
  { method: "POST", body: JSON.stringify({ repository_url: repositoryUrl, use_private_token: usePrivateToken, confirm_read_only_network: true }) },
);
export const listGitHubAnalyses = (projectId: string, signal?: AbortSignal) => apiRequest<GitHubAnalysis[]>(
  `/api/v1/github/projects/${encodeURIComponent(projectId)}/analyses`,
  { signal },
);
export const saveGitHubToken = (token: string) => apiRequest<{ configured: boolean }>(
  "/api/v1/github/token",
  { method: "POST", body: JSON.stringify({ token }) },
);
