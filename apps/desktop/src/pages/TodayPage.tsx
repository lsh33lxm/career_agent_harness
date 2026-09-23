import {
  AlertCircle, CheckCircle2, ChevronRight, FileJson2, FileText, Link2, RefreshCw, ScanText, Upload,
} from "lucide-react";
import { useEffect, useState } from "react";

import { getLegacyKnowledgeOverview } from "../api/legacy";
import { useHealth } from "../api/useHealth";
import { useToday } from "../api/useToday";
import {
  previewFeishuToday,
  type FeishuTodayPreview,
  type TodayItem,
  type TodayItemKind,
  type TodayQueue,
} from "../api/today";
import type { PriorityLevel } from "../api/client";

const priorityLabels: Record<PriorityLevel, string> = {
  urgent: "紧急",
  high: "高",
  medium: "中",
  low: "低",
};

// Display labels only; the Core response order and reasons are rendered as-is.
const kindLabels: Record<TodayItemKind, string> = {
  opportunity_action: "机会行动",
  application_step: "申请步骤",
  interview_prep: "面试准备",
  enhancement_task: "增强任务",
  review_request: "待你确认",
};
const sourceKindLabels: Record<string, string> = {
  opportunity: "机会",
  application: "申请",
  interview: "面试",
  capability: "能力",
  review_request: "待确认",
  project: "项目",
};

const weekdayLabels = ["日", "一", "二", "三", "四", "五", "六"];

function todayDateLabel(): string {
  const now = new Date();
  return `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日  星期${weekdayLabels[now.getDay()]}`;
}

function formatDataTime(iso: string): string {
  return iso.replace("T", " ").slice(0, 16);
}

function TodayItemCard({ item }: { item: TodayItem }) {
  const times: Array<{ label: string; value: string }> = [];
  if (item.deadline_at !== null) {
    times.push({ label: "截止", value: formatDataTime(item.deadline_at) });
  }
  if (item.interview_at !== null) {
    times.push({ label: "面试", value: formatDataTime(item.interview_at) });
  }
  return (
    <article className="today-opportunity">
      <div className="company-glyph" aria-hidden="true">{kindLabels[item.kind].slice(0, 1)}</div>
      <div className="today-opportunity-name">
        <h3>{kindLabels[item.kind]}</h3>
        <span>{item.item_id}</span>
        <small>
          来源 <mark>{item.source_refs.map((ref) => `${sourceKindLabels[ref.kind] ?? "来源"}：${ref.entity_id}#${ref.revision}`).join("、")}</mark>
        </small>
      </div>
      <div className="today-match">
        {times.length === 0
          ? <><strong>—</strong><span>无时限</span></>
          : times.map((time) => (
            <span key={time.label}><strong>{time.value}</strong><span>{time.label}</span></span>
          ))}
      </div>
      <div className="today-opportunity-reason">
        {item.reasons.map((reason) => <p key={reason.code}>{reason.explanation}</p>)}
        <div className="priority-pair">
          <span>系统建议 {item.suggested_priority === null ? "未评估" : priorityLabels[item.suggested_priority]}</span>
          <span>用户优先级 {item.user_priority === null ? "未设置" : priorityLabels[item.user_priority]}</span>
        </div>
      </div>
      <ChevronRight size={18} aria-hidden="true" />
    </article>
  );
}

function TodayQueuePanel({ queue, legacyJobCount }: { queue: TodayQueue; legacyJobCount: number | null }) {
  return (
    <section className="today-panel opportunity-stream" aria-labelledby="queue-title">
      <div className="today-section-heading">
        <h2 className="today-section-title" id="queue-title">
          <span />今日队列{" "}
          <small>
            数据时点 {formatDataTime(queue.generated_at)} · {queue.items.length} 项 · {queue.input_revisions.length} 个输入修订
          </small>
        </h2>
      </div>
      {queue.items.length === 0
        ? (
          <div className="empty-state">
            {legacyJobCount && legacyJobCount > 0 ? (
              <>
                <p>Core 今日队列为空，但已有 {legacyJobCount} 条历史岗位可查看。</p>
                <a className="today-secondary" href="/opportunities">前往机会选择岗位</a>
                <small>历史岗位不会自动进入求职流程，也不会改变用户优先级。</small>
              </>
            ) : <p>今日队列为空。先在“机会”导入或选择岗位，建立下一步行动。</p>}
          </div>
        )
        : (
          <div className="today-opportunities">
            {queue.items.map((item) => <TodayItemCard item={item} key={item.item_id} />)}
          </div>
        )}
    </section>
  );
}

export function TodayPage() {
  const [legacyJobCount, setLegacyJobCount] = useState<number | null>(null);
  const [feishuPreview, setFeishuPreview] = useState<
    { status: "idle" | "loading" } | { status: "ready"; data: FeishuTodayPreview } | { status: "error"; message: string }
  >({ status: "idle" });
  const [health, retryHealth] = useHealth();
  const [today, retryToday] = useToday();
  const firstItem = today.status === "ready" ? today.data.items[0] : undefined;
  const reviews = today.status === "ready"
    ? today.data.items.filter((item) => item.kind === "review_request") : [];
  const unavailable = today.status === "loading" ? "正在读取今日队列…" : "队列暂不可用，恢复连接后显示。";
  useEffect(() => {
    const controller = new AbortController();
    getLegacyKnowledgeOverview(controller.signal)
      .then((overview) => setLegacyJobCount(overview.job_count))
      .catch(() => {
        if (!controller.signal.aborted) setLegacyJobCount(null);
      });
    return () => controller.abort();
  }, []);
  const generateFeishuPreview = async () => {
    setFeishuPreview({ status: "loading" });
    try {
      setFeishuPreview({ status: "ready", data: await previewFeishuToday() });
    } catch (error) {
      setFeishuPreview({
        status: "error",
        message: error instanceof Error ? error.message : "生成失败",
      });
    }
  };
  return (
    <main className="today-page">
      <header className="today-hero">
        <div>
          <div className="today-title-row"><h1>今天</h1><time>{todayDateLabel()}</time></div>
          <p>在不确定的时代，做更清醒的选择。</p>
        </div>
        <div className="today-sunrise" aria-hidden="true">
          <span className="sunrise-sun" /><span className="sunrise-hill sunrise-hill--near" />
          <span className="sunrise-hill sunrise-hill--far" />
        </div>
        <p className="today-motto">积累真实的自己<br />走向更大的可能</p>
        <div className={`service-status service-status--${health.status}`} aria-live="polite">
          {health.status === "loading" && <span className="status-spinner" aria-hidden="true" />}
          {health.status === "online" && <CheckCircle2 size={16} aria-hidden="true" />}
          {health.status === "offline" && <AlertCircle size={16} aria-hidden="true" />}
          <span>{health.status === "online" ? `Core ${health.data.version}` : health.status === "loading" ? "连接中" : "Core 离线"}</span>
          {health.status === "offline" && <button type="button" onClick={retryHealth} title="重试连接" aria-label="重试连接"><RefreshCw size={15} /></button>}
        </div>
      </header>

      <div className="today-layout">
        <div className="today-main-column">
          <section className="today-panel focus-panel" aria-labelledby="focus-title">
            <h2 className="today-section-title" id="focus-title"><span />今日焦点</h2>
            <div className="today-focus-summary">
              {firstItem ? <>
                <h3>{kindLabels[firstItem.kind]}</h3>
                <p>{firstItem.item_id}</p>
                <small>沿用今日队列首项，不另行排序。完整理由与来源见下方队列。</small>
                <a className="today-secondary" href="#queue-title">查看队列</a>
              </> : today.status === "ready" && legacyJobCount && legacyJobCount > 0 ? <>
                <h3>已有 {legacyJobCount} 条历史岗位</h3>
                <p>先在“机会”中选择一个岗位加入求职流程，Core 才会生成可审计的今日行动。</p>
                <a className="today-secondary" href="/opportunities">查看历史岗位</a>
              </> : <p>{today.status === "ready" ? "暂无焦点。先导入或选择岗位，建立今天的第一步。" : unavailable}</p>}
            </div>
          </section>
          {today.status === "loading" && (
            <section className="today-panel opportunity-stream" aria-label="今日队列加载中">
              <div className="empty-state">
                <span className="status-spinner" aria-hidden="true" />
                <p>正在加载今日队列…</p>
              </div>
            </section>
          )}
          {today.status === "error" && (
            <section className="today-panel opportunity-stream" aria-labelledby="queue-error-title">
              <h2 className="today-section-title" id="queue-error-title"><span />今日队列</h2>
              <div className="fatal-state" role="alert">
                <p>Core 暂不可用：{today.message}</p>
                <button type="button" onClick={retryToday}>重试</button>
              </div>
            </section>
          )}
          {today.status === "ready" && <TodayQueuePanel queue={today.data} legacyJobCount={legacyJobCount} />}
          <section className="today-panel weekly-panel" aria-labelledby="weekly-title">
            <h2 className="today-section-title" id="weekly-title"><span />本周回看</h2>
            <p className="today-unavailable">周度回看尚未接入，当前不展示进度或完成数量。</p>
            <blockquote>积累真实的自己，走向更大的可能。</blockquote>
          </section>
        </div>

        <aside className="today-side-column">
          <section className="today-panel confirmation-panel" aria-labelledby="confirmation-title">
            <h2 className="today-section-title" id="confirmation-title"><span />需要你确认</h2>
            {today.status !== "ready" ? <p className="today-unavailable">{unavailable}</p>
              : reviews.length === 0 ? <p className="today-unavailable">今日队列中暂无待确认事项。</p>
                : <ul className="today-review-list">{reviews.map((item) => <li key={item.item_id}>
                  <strong>{item.item_id}</strong>
                  {item.reasons.map((reason) => <p key={reason.code}>{reason.explanation}</p>)}
                </li>)}</ul>}
            <small>仅展示队列中的待确认项；本页不执行审批。</small>
          </section>
          <section className="today-panel feishu-preview-panel" aria-labelledby="feishu-preview-title">
            <h2 className="today-section-title" id="feishu-preview-title"><span />飞书离线预览</h2>
            <p>把当前 Core 今日队列生成可审计 JSON；不会连接或写入飞书。</p>
            <button
              className="today-secondary"
              type="button"
              disabled={today.status !== "ready" || feishuPreview.status === "loading"}
              onClick={generateFeishuPreview}
            >
              <FileJson2 size={16} />
              {feishuPreview.status === "loading" ? "正在生成…" : "生成离线预览"}
            </button>
            {feishuPreview.status === "ready" && <div className="feishu-preview-result" aria-live="polite">
              <strong>{feishuPreview.data.rows.length} 行 · {feishuPreview.data.schema_version}</strong>
              <small>来源摘要 {feishuPreview.data.source_sha256.slice(0, 16)}… · 仅 dry-run</small>
              {feishuPreview.data.rows.length === 0
                ? <p>当前 Today 队列为空，预览没有行。</p>
                : <ol>{feishuPreview.data.rows.slice(0, 3).map((row) => (
                  <li key={row.item.item_id}>{row.ordinal}. {kindLabels[row.item.kind]} · {row.item.item_id}</li>
                ))}</ol>}
            </div>}
            {feishuPreview.status === "error" && <p className="today-unavailable" role="alert">预览生成失败：{feishuPreview.message}</p>}
            <small>真实同步仍需凭据、目标权限和逐次批准。</small>
          </section>
          <section className="today-panel capture-panel" aria-labelledby="capture-title">
            <h2 className="today-section-title" id="capture-title"><span />快速收集</h2>
            <button className="capture-input" type="button" disabled><Link2 size={17} />粘贴链接（职位、文章、公司页面等）</button>
            <div className="capture-tools"><button type="button" disabled><Upload size={16} />上传 PDF</button><button type="button" disabled><ScanText size={16} />截图识别</button><button type="button" disabled><FileText size={16} />粘贴文本</button></div>
            <p>收集入口尚未接入，暂不可用。</p>
            <p className="capture-note">稳步前行<br />已经走在更好的路上</p>
          </section>
        </aside>
      </div>
    </main>
  );
}
