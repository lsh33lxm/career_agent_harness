import { apiRequest } from "./client";

export type CommunicationStatus =
  | "pending_review" | "approved" | "rejected" | "sent" | "replied" | "follow_up" | "closed" | "blocked";

export interface CommunicationDraft {
  draft_id: string;
  opportunity_id: string;
  source_staging_id: string | null;
  channel: "email" | "platform_message" | "follow_up_note";
  recipient: string | null;
  body: string;
  status: CommunicationStatus;
  provenance: Record<string, string>;
  reviewed_by: string | null;
  review_reason: string | null;
}

export interface CommunicationSummary {
  daily_limit: number;
  created_today: number;
  remaining_today: number;
  counts: Record<string, number>;
  channel_counts: Record<string, number>;
  reply_count: number;
  follow_up_count: number;
}

export function listCommunicationDrafts(): Promise<CommunicationDraft[]> {
  return apiRequest<CommunicationDraft[]>("/api/v1/communications/drafts");
}

export function getCommunicationSummary(): Promise<CommunicationSummary> {
  return apiRequest<CommunicationSummary>("/api/v1/communications/summary");
}

export function createCommunicationDraft(input: {
  draft_id: string; opportunity_id: string; source_staging_id?: string;
  channel: CommunicationDraft["channel"]; recipient?: string; body: string;
  provenance?: Record<string, string>;
}): Promise<CommunicationDraft> {
  return apiRequest<CommunicationDraft>("/api/v1/communications/drafts", {
    method: "POST", body: JSON.stringify(input),
  });
}

export function reviewCommunicationDraft(
  draftId: string, decision: "approved" | "rejected", reason: string,
): Promise<CommunicationDraft> {
  return apiRequest<CommunicationDraft>(`/api/v1/communications/drafts/${encodeURIComponent(draftId)}/review`, {
    method: "POST", body: JSON.stringify({ decision, reason }),
  });
}

export interface MailboxAccount {
  account_id: string;
  display_name: string;
  provider: string;
  username: string;
  imap_host: string;
  imap_port: number;
  security: "ssl" | "starttls";
  credential_ref: string;
  enabled: boolean;
  last_test_status: string | null;
  last_error_code: string | null;
}

export interface MailMessage {
  message_id: string;
  account_id: string;
  folder: string;
  sender: string | null;
  subject: string | null;
  received_at: string | null;
  preview: string;
  opportunity_id: string | null;
  application_id: string | null;
}

export function listMailboxAccounts(): Promise<MailboxAccount[]> {
  return apiRequest<MailboxAccount[]>("/api/v1/mailbox/accounts");
}

export function saveMailboxAccount(input: {
  account_id: string; display_name: string; provider: string; username: string;
  imap_host: string; imap_port: number; security: "ssl" | "starttls"; secret: string;
}): Promise<MailboxAccount> {
  return apiRequest<MailboxAccount>("/api/v1/mailbox/accounts", { method: "POST", body: JSON.stringify(input) });
}

export function testMailboxAccount(account_id: string): Promise<{ account_id: string; status: string; message?: string }> {
  return apiRequest("/api/v1/mailbox/test", { method: "POST", body: JSON.stringify({ account_id }) });
}

export function fetchMailboxMessages(account_id: string, folder = "INBOX", limit = 20): Promise<MailMessage[]> {
  return apiRequest<MailMessage[]>(`/api/v1/mailbox/${encodeURIComponent(account_id)}/messages?folder=${encodeURIComponent(folder)}&limit=${limit}`, { method: "POST" });
}

export function listMailboxMessages(account_id: string): Promise<MailMessage[]> {
  return apiRequest<MailMessage[]>(`/api/v1/mailbox/${encodeURIComponent(account_id)}/messages`);
}

export function associateMailboxMessage(message_id: string, input: { opportunity_id?: string; application_id?: string }): Promise<MailMessage> {
  return apiRequest<MailMessage>(`/api/v1/mailbox/messages/${encodeURIComponent(message_id)}/association`, {
    method: "PATCH", body: JSON.stringify(input),
  });
}

export function transitionCommunicationDraft(draftId: string, status: CommunicationStatus): Promise<CommunicationDraft> {
  return apiRequest<CommunicationDraft>(`/api/v1/communications/drafts/${encodeURIComponent(draftId)}/transition`, {
    method: "POST", body: JSON.stringify({ status }),
  });
}
