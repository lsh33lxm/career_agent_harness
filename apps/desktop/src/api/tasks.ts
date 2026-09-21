import { apiRequest } from "./client";

export type TaskStatus =
  | "pending"
  | "processing"
  | "completed"
  | "failed"
  | "cancelled"
  | "retrying"
  | "finalizing"
  | "dead_letter";

export interface TaskRecord {
  task_id: string;
  task_type: string;
  stage: string;
  status: TaskStatus;
  progress: number;
  current_attempt: number;
  max_attempts: number;
  version: number;
  available_at: string;
  claimed_at: string | null;
  created_at: string;
  updated_at: string;
  last_error: string | null;
}

export interface TaskAttempt {
  task_id: string;
  attempt: number;
  task_version: number;
  status: "completed" | "failed" | "cancelled" | "stale";
  error_type: string | null;
  error_message: string | null;
  started_at: string;
  finished_at: string;
}

export interface TaskDetail {
  task: TaskRecord;
  attempts: TaskAttempt[];
}

export const listTasks = (signal?: AbortSignal) =>
  apiRequest<TaskRecord[]>("/api/v1/tasks?limit=100", { signal });

export const getTask = (taskId: string) =>
  apiRequest<TaskDetail>(`/api/v1/tasks/${encodeURIComponent(taskId)}`);

export const retryTask = (taskId: string) =>
  apiRequest<TaskRecord>(`/api/v1/tasks/${encodeURIComponent(taskId)}/retry`, { method: "POST" });

export const runTaskStage = (stage: string) =>
  apiRequest<TaskRecord[]>(`/api/v1/tasks/stages/${encodeURIComponent(stage)}/run`, { method: "POST" });
