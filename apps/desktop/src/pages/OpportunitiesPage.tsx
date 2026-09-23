import { BriefcaseBusiness, Check, MessagesSquare } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  getOpportunity,
  listOpportunities,
  setOpportunityUserPriority,
  type OpportunitySummary,
  type PriorityLevel,
} from "../api/client";
import { localizedApiError } from "../api/client";
import { JobRadarPanel } from "./JobRadarPanel";
import { createCommunicationDraft, getCommunicationSummary, listCommunicationDrafts, reviewCommunicationDraft, type CommunicationDraft, type CommunicationSummary } from "../api/communications";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { ErrorNotice, InlineNotice } from "../components/ui/Notice";

const priorityLevels: PriorityLevel[] = ["low", "medium", "high", "urgent"];
const priorityLabels: Record<PriorityLevel, string> = {
  low: "低",
  medium: "中",
  high: "高",
  urgent: "紧急",
};
const stateLabels: Record<string, string> = {
  discovered: "已发现",
  qualified: "已确认",
  watching: "关注中",
  preparing: "准备中",
  applied: "已投递",
  interviewing: "面试中",
  closed: "已结束",
};

type LoadState = "loading" | "ready" | "error";

function requestId(prefix: string): string {
  const suffix = globalThis.crypto.randomUUID?.().replaceAll("-", "_")
    ?? `${Date.now()}_${Math.random().toString(36).slice(2)}`;
  return `${prefix}_${suffix}`;
}

function errorMessage(error: unknown): string {
  return localizedApiError(error);
}

export function OpportunitiesPage() {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [items, setItems] = useState<OpportunitySummary[]>([]);
  const [loadError, setLoadError] = useState("");
  const [priorityDrafts, setPriorityDrafts] = useState<Record<string, PriorityLevel | "">>({});
  const [priorityReasons, setPriorityReasons] = useState<Record<string, string>>({});
  const [priorityPending, setPriorityPending] = useState<Record<string, boolean>>({});
  const [priorityErrors, setPriorityErrors] = useState<Record<string, string>>({});
  const [drafts, setDrafts] = useState<CommunicationDraft[]>([]);
  const [communicationSummary, setCommunicationSummary] = useState<CommunicationSummary | null>(null);
  const [draftBody, setDraftBody] = useState("");
  const [draftMessage, setDraftMessage] = useState("");
  const [draftDetail, setDraftDetail] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoadState("loading");
    setLoadError("");
    try {
      setItems(await listOpportunities(signal));
      setPriorityErrors({});
      setLoadState("ready");
    } catch (error) {
      if (!signal?.aborted) {
        setLoadError(errorMessage(error));
        setLoadState("error");
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    void Promise.all([listCommunicationDrafts(), getCommunicationSummary()])
      .then(([draftItems, summary]) => { setDrafts(draftItems); setCommunicationSummary(summary); })
      .catch(() => setDraftMessage("沟通草稿暂不可用"));
  }, []);

  async function createDraft() {
    const item = items[0];
    if (!item || !draftBody.trim()) return;
    try {
      const created = await createCommunicationDraft({
        draft_id: requestId("draft"), opportunity_id: item.opportunity.entity_id,
        channel: "follow_up_note", body: draftBody.trim(), provenance: { source: "user", mode: "local" },
      });
      setDrafts((current) => [created, ...current]);
      setDraftBody(""); setDraftMessage("草稿已保存，等待你审核；不会自动发送。");
      setDraftDetail("");
    } catch (error) {
      setDraftMessage("草稿保存失败，请重试。");
      setDraftDetail(errorMessage(error));
    }
  }

  async function reviewDraft(draft: CommunicationDraft, decision: "approved" | "rejected") {
    try {
      const updated = await reviewCommunicationDraft(draft.draft_id, decision, decision === "approved" ? "用户确认草稿" : "用户拒绝草稿");
      setDrafts((current) => current.map((item) => item.draft_id === updated.draft_id ? updated : item));
      setDraftDetail("");
    } catch (error) {
      setDraftMessage("草稿审核失败，请重试。");
      setDraftDetail(errorMessage(error));
    }
  }

  async function handlePriority(event: FormEvent<HTMLFormElement>, item: OpportunitySummary) {
    event.preventDefault();
    const opportunityId = item.opportunity.entity_id;
    const level = priorityDrafts[opportunityId] ?? item.user_priority?.level ?? "";
    if (!level) return;

    const reason = priorityReasons[opportunityId]?.trim();
    setPriorityPending((current) => ({ ...current, [opportunityId]: true }));
    setPriorityErrors((current) => ({ ...current, [opportunityId]: "" }));
    try {
      await setOpportunityUserPriority(
        opportunityId,
        {
          command_id: requestId("command"),
          expected_revision: item.opportunity.revision,
          level,
          ...(reason ? { reason } : {}),
        },
        requestId("user_priority"),
      );
      const updated = await getOpportunity(opportunityId);
      setItems((current) => current.map((value) => (
        value.opportunity.entity_id === opportunityId ? updated : value
      )));
      setPriorityDrafts((current) => ({
        ...current,
        [opportunityId]: updated.user_priority?.level ?? "",
      }));
      setPriorityReasons((current) => ({ ...current, [opportunityId]: "" }));
    } catch (error) {
      setPriorityErrors((current) => ({
        ...current,
        [opportunityId]: errorMessage(error),
      }));
    } finally {
      setPriorityPending((current) => ({ ...current, [opportunityId]: false }));
    }
  }

  return (
    <main className="page page--wide">
      <PageHeader
        eyebrow="职业机会"
        title="机会"
        description="先查看历史岗位与来源证据，再由你决定是否加入求职流程。"
      />

      <JobRadarPanel />

      <Surface className="surface--flow">
        <Section
          title="沟通草稿"
          icon={MessagesSquare}
          description="草稿只保存在本地，批准也不会自动发送。"
          meta={`${drafts.length} 条`}
        >
          {communicationSummary && <div className="summary-strip" aria-label="沟通摘要">
            <span>今日新增 {communicationSummary.created_today}/{communicationSummary.daily_limit}</span>
            <span>剩余 {communicationSummary.remaining_today}</span>
            <span>已回复 {communicationSummary.reply_count}</span>
            <span>待跟进 {communicationSummary.follow_up_count}</span>
            <span>邮件 {communicationSummary.channel_counts.email ?? 0}</span>
            <span>平台消息 {communicationSummary.channel_counts.platform_message ?? 0}</span>
          </div>}
          <div className="draft-composer">
            <Field label="新建草稿">
              <textarea
                className="textarea"
                aria-label="沟通草稿内容"
                value={draftBody}
                onChange={(event) => setDraftBody(event.target.value)}
                placeholder="写下跟进或沟通草稿"
              />
            </Field>
            <Button
              variant="primary"
              onClick={() => void createDraft()}
              disabled={!items.length || !draftBody.trim()}
            >
              保存草稿
            </Button>
          </div>
          {draftMessage && (
            <div style={{ marginTop: "var(--space-3)" }}>
              {draftDetail
                ? <ErrorNotice label={draftMessage} detail={draftDetail} />
                : <InlineNotice tone={draftMessage.includes("已保存") ? "success" : "muted"} role="status">{draftMessage}</InlineNotice>}
            </div>
          )}
          {drafts.length > 0 && (
            <div className="draft-list">
              {drafts.map((draft) => { const statusLabel = draft.status === "pending_review" ? "待确认" : draft.status === "approved" ? "已批准" : draft.status === "rejected" ? "已拒绝" : draft.status === "sent" ? "已记录发送" : draft.status === "replied" ? "已回复" : draft.status === "follow_up" ? "待跟进" : draft.status === "closed" ? "已结束" : draft.status === "blocked" ? "已阻断" : "待确认"; const blockedReason = draft.provenance.blocked_reason === "daily_communication_limit" ? "已达到今日沟通上限，草稿仍保留在本地。" : null; return (
                <article className="draft-item" key={draft.draft_id}>
                  <div className="draft-item__head">
                    <span className={draft.status === "pending_review" ? "badge badge--gold" : draft.status === "rejected" || draft.status === "blocked" ? "badge badge--danger" : "badge badge--green"}>{statusLabel}</span>
                    {draft.status === "pending_review" && (
                      <div className="draft-item__actions">
                        <Button size="sm" variant="primary" onClick={() => void reviewDraft(draft, "approved")}>确认草稿</Button>
                        <Button size="sm" variant="secondary" onClick={() => void reviewDraft(draft, "rejected")}>拒绝</Button>
                      </div>
                    )}
                  </div>
                  <p>{draft.body}</p>
                  {blockedReason && <InlineNotice tone="muted">{blockedReason}</InlineNotice>}
                </article>
              ); })}
            </div>
          )}
        </Section>
      </Surface>

      <Surface>
        <Section
          title="求职流程"
          icon={BriefcaseBusiness}
          description="只有经过你确认的岗位才会进入这里；优先级由你保存。"
          meta={loadState === "ready" ? `${items.length} 项` : undefined}
        >
          {loadState === "loading" && <LoadingState label="正在读取求职流程…" />}

          {loadState === "error" && (
            <ErrorState
              title="暂时无法读取求职流程"
              description="恢复连接后重试即可，已确认的内容不会丢失。"
              detail={loadError}
              onRetry={() => void load()}
            />
          )}

          {loadState === "ready" && items.length === 0 && (
            <EmptyState
              icon={BriefcaseBusiness}
              title="还没有加入求职流程的岗位"
              description="在上方历史岗位库中选择岗位，查看详情后点击“加入求职流程”。"
            />
          )}

          {loadState === "ready" && items.length > 0 && (
            <div className="opportunity-records">
              {items.map((item, index) => {
                const opportunityId = item.opportunity.entity_id;
                const selectedPriority = priorityDrafts[opportunityId] ?? item.user_priority?.level ?? "";
                const priorityError = priorityErrors[opportunityId];
                return (
                  <article className="opportunity-record" key={opportunityId}>
                    <header className="opportunity-record__head">
                      <div>
                        <h3>求职机会 {index + 1}</h3>
                        <p className="text-aux">{stateLabels[item.opportunity.state] ?? "进行中"}</p>
                      </div>
                    </header>

                    <div className="priority-grid">
                      <section className="priority-cell" aria-label={`求职机会 ${index + 1} 的建议优先级`}>
                        <div className="priority-cell__head">
                          <h4>系统建议</h4>
                          {item.suggested_priority ? (
                            <span className={`priority-badge priority-badge--${item.suggested_priority.level}`}>
                              {priorityLabels[item.suggested_priority.level]}
                            </span>
                          ) : (
                            <span className="text-aux">暂无建议</span>
                          )}
                        </div>
                        {item.suggested_priority && (
                          <ul>{item.suggested_priority.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                        )}
                      </section>

                      <section className="priority-cell" aria-label={`求职机会 ${index + 1} 的用户优先级`}>
                        <div className="priority-cell__head">
                          <h4>我的优先级</h4>
                          {item.user_priority ? (
                            <span className={`priority-badge priority-badge--${item.user_priority.level}`}>
                              {priorityLabels[item.user_priority.level]}
                            </span>
                          ) : (
                            <span className="text-aux">尚未设置</span>
                          )}
                        </div>
                        <form className="priority-form" onSubmit={(event) => void handlePriority(event, item)}>
                          <select
                            className="select"
                            aria-label={`选择求职机会 ${index + 1} 的优先级`}
                            value={selectedPriority}
                            onChange={(event) => setPriorityDrafts((current) => ({
                              ...current,
                              [opportunityId]: event.target.value as PriorityLevel | "",
                            }))}
                          >
                            <option value="">选择优先级</option>
                            {priorityLevels.map((level) => <option key={level} value={level}>{priorityLabels[level]}</option>)}
                          </select>
                          <input
                            className="input"
                            aria-label={`填写求职机会 ${index + 1} 的优先级原因`}
                            value={priorityReasons[opportunityId] ?? ""}
                            onChange={(event) => setPriorityReasons((current) => ({
                              ...current,
                              [opportunityId]: event.target.value,
                            }))}
                            maxLength={2048}
                            placeholder="原因（可选）"
                          />
                          <Button
                            variant="secondary"
                            type="submit"
                            loading={priorityPending[opportunityId]}
                            disabled={!selectedPriority}
                            icon={<Check size={15} aria-hidden="true" />}
                          >
                            {priorityPending[opportunityId] ? "保存中…" : "保存"}
                          </Button>
                          {priorityError && (
                            <div style={{ gridColumn: "1 / -1" }}>
                              <ErrorNotice label="保存优先级失败，请重试。" detail={priorityError} />
                            </div>
                          )}
                        </form>
                      </section>
                    </div>
                  </article>
                );
              })}
            </div>
          )}
        </Section>
      </Surface>
    </main>
  );
}
