import { apiRequest } from "./client";

export type ConnectorStatus = "active" | "paused";

export interface SourceConnector {
  connector_id: string;
  connector_type: "local_folder" | "legacy_agent_radar" | "github";
  display_name: string;
  status: ConnectorStatus;
  config: {
    root_path?: string;
    repository_url?: string;
    use_private_token?: boolean;
    read_only_network_confirmed?: boolean;
  };
  sync_cursor: Record<string, unknown> | null;
  conflict_policy: "source_wins" | "local_wins" | "defer";
  delete_policy: "keep" | "mark_deleted";
  created_at: string;
  updated_at: string;
}

export interface SourceSyncRun {
  sync_run_id: string;
  connector_id: string;
  mode: "full" | "incremental";
  status: "processing" | "completed" | "failed";
  stats: { created: number; updated: number; skipped: number; deleted: number; failed: number };
  error: string | null;
  started_at: string;
  finished_at: string | null;
}

export interface SourceSyncTask {
  status: "pending" | "processing" | "completed" | "failed" | "cancelled" | "retrying" | "finalizing" | "dead_letter";
  last_error: string | null;
}

export function listSourceConnectors(signal?: AbortSignal): Promise<SourceConnector[]> {
  return apiRequest<SourceConnector[]>("/api/v1/source-connectors", { signal });
}

export function createLocalFolderConnector(
  displayName: string,
  rootPath: string,
): Promise<SourceConnector> {
  return apiRequest<SourceConnector>("/api/v1/source-connectors/local-folder", {
    method: "POST",
    body: JSON.stringify({ display_name: displayName, root_path: rootPath }),
  });
}

export interface SourceConnectionTest {
  ok: boolean;
  connector_type: SourceConnector["connector_type"];
  network_verified?: boolean;
  last_verified_commit?: string | null;
}

export function testSourceConnector(connectorId: string): Promise<SourceConnectionTest> {
  return apiRequest<SourceConnectionTest>(
    `/api/v1/source-connectors/${encodeURIComponent(connectorId)}/test`,
    { method: "POST" },
  );
}

export function syncSourceConnector(connectorId: string): Promise<SourceSyncTask> {
  return apiRequest<SourceSyncTask>(
    `/api/v1/source-connectors/${encodeURIComponent(connectorId)}/sync`,
    { method: "POST", body: JSON.stringify({ mode: "incremental" }) },
  );
}

export function setSourceConnectorPaused(
  connectorId: string,
  paused: boolean,
): Promise<SourceConnector> {
  return apiRequest<SourceConnector>(
    `/api/v1/source-connectors/${encodeURIComponent(connectorId)}/${paused ? "pause" : "resume"}`,
    { method: "POST" },
  );
}

export function listSourceSyncRuns(
  connectorId: string,
  signal?: AbortSignal,
): Promise<SourceSyncRun[]> {
  return apiRequest<SourceSyncRun[]>(
    `/api/v1/source-connectors/${encodeURIComponent(connectorId)}/runs`,
    { signal },
  );
}
