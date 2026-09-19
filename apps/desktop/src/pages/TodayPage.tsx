import {
  AlertCircle, CheckCircle2, ChevronRight, FileText, Link2, RefreshCw, ScanText, Upload,
} from "lucide-react";

import { useHealth } from "../api/useHealth";
import { useToday } from "../api/useToday";
import type { TodayItem, TodayItemKind, TodayQueue } from "../api/today";
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
          来源 <mark>{item.source_refs.map((ref) => `${ref.kind}:${ref.entity_id}#${ref.revision}`).join("、")}</mark>
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

function TodayQueuePanel({ queue }: { queue: TodayQueue }) {
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
            <p>今日队列为空，Core 没有可展示的事项。</p>
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
  const [health, retryHealth] = useHealth();
  const [today, retryToday] = useToday();
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
          {today.status === "ready" && <TodayQueuePanel queue={today.data} />}
        </div>

        <aside className="today-side-column">
          <section className="today-panel capture-panel" aria-labelledby="capture-title">
            <h2 className="today-section-title" id="capture-title"><span />快速收集</h2>
            <button className="capture-input" type="button"><Link2 size={17} />粘贴链接（职位、文章、公司页面等）</button>
            <div className="capture-tools"><button type="button"><Upload size={16} />上传 PDF</button><button type="button"><ScanText size={16} />截图识别</button><button type="button"><FileText size={16} />粘贴文本</button></div>
            <p>收集有价值的信息，让选择更有依据。</p>
            <p className="capture-note">稳步前行<br />已经走在更好的路上</p>
          </section>
        </aside>
      </div>
    </main>
  );
}
