import { AlertCircle, BriefcaseBusiness, Check, Inbox, RefreshCw } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  getOpportunity,
  listOpportunities,
  setOpportunityUserPriority,
  type OpportunitySummary,
  type PriorityLevel,
} from "../api/client";
import { JobRadarPanel } from "./JobRadarPanel";

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
  return error instanceof Error ? error.message : "本地职业核心暂时不可用";
}

export function OpportunitiesPage() {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [items, setItems] = useState<OpportunitySummary[]>([]);
  const [loadError, setLoadError] = useState("");
  const [priorityDrafts, setPriorityDrafts] = useState<Record<string, PriorityLevel | "">>({});
  const [priorityReasons, setPriorityReasons] = useState<Record<string, string>>({});
  const [priorityPending, setPriorityPending] = useState<Record<string, boolean>>({});
  const [priorityErrors, setPriorityErrors] = useState<Record<string, string>>({});

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
    <main className="page opportunities-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">职业机会</p>
          <h1>机会</h1>
          <p>先查看历史岗位与来源证据，再由你决定是否加入求职流程。</p>
        </div>
      </div>

      <JobRadarPanel />

      <section className="opportunity-list" aria-labelledby="opportunity-list-title">
        <div className="section-heading">
          <div>
            <p className="eyebrow">由你确认</p>
            <h2 id="opportunity-list-title">求职流程</h2>
          </div>
          {loadState === "ready" && <span>{items.length} 项</span>}
        </div>

        {loadState === "loading" && (
          <div className="opportunity-state" aria-live="polite">
            <span className="status-spinner" aria-hidden="true" />
            <p>正在读取求职流程…</p>
          </div>
        )}

        {loadState === "error" && (
          <div className="opportunity-state" role="alert">
            <AlertCircle size={24} aria-hidden="true" />
            <h3>暂时无法读取求职流程</h3>
            <p>{loadError}</p>
            <button className="secondary-command" type="button" onClick={() => void load()}>
              <RefreshCw size={16} aria-hidden="true" />
              <span>重试</span>
            </button>
          </div>
        )}

        {loadState === "ready" && items.length === 0 && (
          <div className="opportunity-state">
            <Inbox size={24} aria-hidden="true" />
            <h3>还没有加入求职流程的岗位</h3>
            <p>在上方历史岗位库中选择岗位，查看详情后点击“加入求职流程”。</p>
          </div>
        )}

        {loadState === "ready" && items.length > 0 && (
          <div className="opportunity-records">
            {items.map((item, index) => {
              const opportunityId = item.opportunity.entity_id;
              const selectedPriority = priorityDrafts[opportunityId] ?? item.user_priority?.level ?? "";
              const priorityError = priorityErrors[opportunityId];
              return (
                <article className="opportunity-record" key={opportunityId}>
                  <header className="record-header">
                    <div className="record-identity">
                      <BriefcaseBusiness size={18} aria-hidden="true" />
                      <div>
                        <h3>求职机会 {index + 1}</h3>
                        <p>{stateLabels[item.opportunity.state] ?? "进行中"}</p>
                      </div>
                    </div>
                  </header>

                  <div className="priority-columns">
                    <section aria-label={`求职机会 ${index + 1} 的建议优先级`}>
                      <div className="priority-heading">
                        <h4>系统建议</h4>
                        {item.suggested_priority ? (
                          <span className={`priority-badge priority-badge--${item.suggested_priority.level}`}>
                            {priorityLabels[item.suggested_priority.level]}
                          </span>
                        ) : (
                          <span className="priority-empty">暂无建议</span>
                        )}
                      </div>
                      {item.suggested_priority && (
                        <ul>{item.suggested_priority.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
                      )}
                    </section>

                    <section aria-label={`求职机会 ${index + 1} 的用户优先级`}>
                      <div className="priority-heading">
                        <h4>我的优先级</h4>
                        {item.user_priority ? (
                          <span className={`priority-badge priority-badge--${item.user_priority.level}`}>
                            {priorityLabels[item.user_priority.level]}
                          </span>
                        ) : (
                          <span className="priority-empty">尚未设置</span>
                        )}
                      </div>
                      <form className="priority-form" onSubmit={(event) => void handlePriority(event, item)}>
                        <label>
                          <span className="sr-only">选择求职机会 {index + 1} 的优先级</span>
                          <select
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
                        </label>
                        <label className="priority-note">
                          <span className="sr-only">填写优先级原因</span>
                          <input
                            aria-label={`填写求职机会 ${index + 1} 的优先级原因`}
                            value={priorityReasons[opportunityId] ?? ""}
                            onChange={(event) => setPriorityReasons((current) => ({
                              ...current,
                              [opportunityId]: event.target.value,
                            }))}
                            maxLength={2048}
                            placeholder="原因（可选）"
                          />
                        </label>
                        <button className="secondary-command" type="submit" disabled={!selectedPriority || priorityPending[opportunityId]}>
                          <Check size={16} aria-hidden="true" />
                          <span>{priorityPending[opportunityId] ? "保存中…" : "保存"}</span>
                        </button>
                      </form>
                      {priorityError && <p className="inline-error" role="alert">{priorityError}</p>}
                    </section>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </main>
  );
}
