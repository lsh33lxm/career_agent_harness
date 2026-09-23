import {
  BriefcaseBusiness, ChartNoAxesColumn, ChevronRight, Crosshair, FileJson2, FileText, Link2,
  ListTodo, MessagesSquare, ScanText, Sparkles, Upload, UserCheck,
} from "lucide-react";
import { useEffect, useState } from "react";

import { getLegacyKnowledgeOverview } from "../api/legacy";
import { useToday } from "../api/useToday";
import {
  previewFeishuToday,
  type FeishuTodayPreview,
  type TodayItem,
  type TodayItemKind,
  type TodayQueue,
} from "../api/today";
import type { PriorityLevel } from "../api/client";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { Button } from "../components/ui/Button";
import { ErrorNotice } from "../components/ui/Notice";

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
  return `${now.getFullYear()}年${now.getMonth() + 1}月${now.getDate()}日 星期${weekdayLabels[now.getDay()]}`;
}

function formatDataTime(iso: string): string {
  return iso.replace("T", " ").slice(0, 16);
}

const itemIcons = {
  opportunity_action: Crosshair,
  application_step: BriefcaseBusiness,
  interview_prep: MessagesSquare,
  enhancement_task: Sparkles,
  review_request: UserCheck,
} as const;

function TodayItemCard({ item }: { item: TodayItem }) {
  const ItemIcon = itemIcons[item.kind];
  const times: Array<{ label: string; value: string }> = [];
  if (item.deadline_at !== null) {
    times.push({ label: "截止", value: formatDataTime(item.deadline_at) });
  }
  if (item.interview_at !== null) {
    times.push({ label: "面试", value: formatDataTime(item.interview_at) });
  }
  return (
    <article className="today-queue-item">
      <span className="section__icon" aria-hidden="true"><ItemIcon size={15} /></span>
      <div className="today-queue-item__name">
        <h3>{kindLabels[item.kind]}</h3>
        <span>{item.item_id}</span>
        <small>
          来源 <mark>{item.source_refs.map((ref) => `${sourceKindLabels[ref.kind] ?? "来源"}：${ref.entity_id}#${ref.revision}`).join("、")}</mark>
        </small>
      </div>
      <div className="today-queue-item__time">
        {times.length === 0
          ? <><strong>—</strong><span>无时限</span></>
          : times.map((time) => (
            <span key={time.label}><strong>{time.value}</strong><span>{time.label}</span></span>
          ))}
      </div>
      <div className="today-queue-item__reason">
        {item.reasons.map((reason) => <p key={reason.code}>{reason.explanation}</p>)}
        <div className="priority-pair">
          <span>系统建议 {item.suggested_priority === null ? "未评估" : priorityLabels[item.suggested_priority]}</span>
          <span>用户优先级 {item.user_priority === null ? "未设置" : priorityLabels[item.user_priority]}</span>
        </div>
      </div>
    </article>
  );
}

function TodayQueuePanel({ queue, legacyJobCount }: { queue: TodayQueue; legacyJobCount: number | null }) {
  return (
    <Section
      title="今日队列"
      icon={ListTodo}
      meta={`数据时点 ${formatDataTime(queue.generated_at)} · ${queue.items.length} 项 · ${queue.input_revisions.length} 个输入修订`}
    >
      {queue.items.length === 0
        ? (
          <EmptyState
            compact
            icon={ChevronRight}
            title={legacyJobCount && legacyJobCount > 0 ? `Core 今日队列为空，但已有 ${legacyJobCount} 条历史岗位可查看。` : "今日队列为空。先在“机会”导入或选择岗位，建立下一步行动。"}
            description={legacyJobCount && legacyJobCount > 0 ? "历史岗位不会自动进入求职流程，也不会改变用户优先级。" : undefined}
            action={legacyJobCount && legacyJobCount > 0
              ? <a className="btn btn--primary" href="/opportunities">前往机会选择岗位</a>
              : undefined}
          />
        )
        : (
          <div>
            {queue.items.map((item) => <TodayItemCard item={item} key={item.item_id} />)}
          </div>
        )}
    </Section>
  );
}

export function TodayPage() {
  const [legacyJobCount, setLegacyJobCount] = useState<number | null>(null);
  const [feishuPreview, setFeishuPreview] = useState<
    { status: "idle" | "loading" } | { status: "ready"; data: FeishuTodayPreview } | { status: "error"; message: string }
  >({ status: "idle" });
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
    <main className="page page--wide">
      <PageHeader
        eyebrow={todayDateLabel()}
        title="今天"
        description="在不确定的时代，做更清醒的选择。"
        art
      />

      <Surface>
        <Section title="今日焦点" icon={Crosshair} ariaLabel="今日焦点">
          <div className="today-focus">
            <div>
              {firstItem ? <>
                <h3>{kindLabels[firstItem.kind]}</h3>
                <p className="text-aux">{firstItem.item_id}</p>
                <p className="text-aux">沿用今日队列首项，不另行排序。完整理由与来源见下方队列。</p>
              </> : today.status === "ready" && legacyJobCount && legacyJobCount > 0 ? <>
                <h3>已有 {legacyJobCount} 条历史岗位</h3>
                <p className="text-aux">先在“机会”中选择一个岗位加入求职流程，Core 才会生成可审计的今日行动。</p>
              </> : <p className="text-aux">{today.status === "ready" ? "暂无焦点。先导入或选择岗位，建立今天的第一步。" : unavailable}</p>}
            </div>
            {firstItem ? <a className="btn btn--primary" href="#today-queue">查看队列</a> : null}
            {!firstItem && today.status === "ready" && legacyJobCount && legacyJobCount > 0
              ? <a className="btn btn--primary" href="/opportunities">查看历史岗位</a>
              : null}
          </div>
        </Section>
      </Surface>

      <div className="today-layout" style={{ marginTop: "var(--space-5)" }}>
        <div className="today-main">
          {today.status === "loading" && (
            <Surface>
              <Section title="今日队列" icon={ListTodo} ariaLabel="今日队列">
                <LoadingState label="正在加载今日队列…" />
              </Section>
            </Surface>
          )}
          {today.status === "error" && (
            <Surface>
              <Section title="今日队列" icon={ListTodo} ariaLabel="今日队列">
                <ErrorState
                  title="Core 暂不可用"
                  description="今日队列暂时无法读取，恢复连接后即可查看。"
                  detail={today.message}
                  onRetry={retryToday}
                />
              </Section>
            </Surface>
          )}
          {today.status === "ready" && (
            <Surface>
              <div id="today-queue">
                <TodayQueuePanel queue={today.data} legacyJobCount={legacyJobCount} />
              </div>
            </Surface>
          )}

          <Surface>
            <Section title="需要你确认" icon={UserCheck} ariaLabel="需要你确认">
              {today.status !== "ready" ? <p className="text-aux">{unavailable}</p>
                : reviews.length === 0 ? <p className="text-aux">今日队列中暂无待确认事项。</p>
                  : <ul className="review-list">{reviews.map((item) => <li key={item.item_id}>
                    <strong>{item.item_id}</strong>
                    {item.reasons.map((reason) => <p key={reason.code}>{reason.explanation}</p>)}
                  </li>)}</ul>}
              <p className="text-aux" style={{ marginTop: "var(--space-3)" }}>仅展示队列中的待确认项；本页不执行审批。</p>
            </Section>
          </Surface>
        </div>

        <aside className="today-side">
          <Surface>
            <Section title="本周回看" icon={ChartNoAxesColumn} ariaLabel="本周回看">
              <p className="text-aux">周度回看尚未接入，当前不展示进度或完成数量。</p>
              <blockquote className="today-quote">积累真实的自己，走向更大的可能。</blockquote>
            </Section>
          </Surface>

          <Surface>
            <Section
              title="飞书离线预览"
              icon={FileJson2}
              ariaLabel="飞书离线预览"
              description="把当前 Core 今日队列生成可审计 JSON；不会连接或写入飞书。"
            >
              <Button
                variant="primary"
                loading={feishuPreview.status === "loading"}
                disabled={today.status !== "ready"}
                onClick={() => void generateFeishuPreview()}
                icon={<FileJson2 size={15} aria-hidden="true" />}
              >
                {feishuPreview.status === "loading" ? "正在生成…" : "生成离线预览"}
              </Button>
              {feishuPreview.status === "ready" && <div className="feishu-result" aria-live="polite" style={{ marginTop: "var(--space-3)" }}>
                <strong>{feishuPreview.data.rows.length} 行 · {feishuPreview.data.schema_version}</strong>
                <small>来源摘要 {feishuPreview.data.source_sha256.slice(0, 16)}… · 仅 dry-run</small>
                {feishuPreview.data.rows.length === 0
                  ? <p className="text-aux">当前 Today 队列为空，预览没有行。</p>
                  : <ol>{feishuPreview.data.rows.slice(0, 3).map((row) => (
                    <li key={row.item.item_id}>{row.ordinal}. {kindLabels[row.item.kind]} · {row.item.item_id}</li>
                  ))}</ol>}
              </div>}
              {feishuPreview.status === "error" && (
                <div style={{ marginTop: "var(--space-3)" }}>
                  <ErrorNotice label="预览生成失败，请重试。" detail={feishuPreview.message} />
                </div>
              )}
              <p className="text-aux" style={{ marginTop: "var(--space-3)" }}>真实同步仍需凭据、目标权限和逐次批准。</p>
            </Section>
          </Surface>

          <Surface>
            <Section title="快速收集" icon={Link2} ariaLabel="快速收集" description="收集入口尚未接入，暂不可用。">
              <div className="capture-grid">
                <Button variant="secondary" disabled icon={<Link2 size={15} aria-hidden="true" />}>粘贴链接</Button>
                <Button variant="secondary" disabled icon={<Upload size={15} aria-hidden="true" />}>上传 PDF</Button>
                <Button variant="secondary" disabled icon={<ScanText size={15} aria-hidden="true" />}>截图识别</Button>
                <Button variant="secondary" disabled icon={<FileText size={15} aria-hidden="true" />}>粘贴文本</Button>
              </div>
            </Section>
          </Surface>
        </aside>
      </div>
    </main>
  );
}
