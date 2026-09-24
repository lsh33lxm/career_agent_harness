import { CalendarDays, ClipboardList, Clock3 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { listApplications, listInterviews, type ApplicationRead, type InterviewRead } from "../api/history";
import { localizedApiError } from "../api/client";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";

const columns: Array<{ state: ApplicationRead["state"]; label: string }> = [
  { state: "preparing", label: "准备中" },
  { state: "ready_for_review", label: "待本人确认" },
  { state: "submitted_by_user", label: "已确认投递" },
  { state: "screen", label: "筛选中" },
  { state: "oa", label: "在线测评" },
  { state: "interview", label: "面试中" },
  { state: "offer", label: "Offer" },
  { state: "rejected", label: "未通过" },
];

function dateLabel(value: string): string {
  return new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}

export function ApplicationsPage() {
  const [applications, setApplications] = useState<ApplicationRead[]>([]);
  const [interviews, setInterviews] = useState<InterviewRead[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    Promise.resolve(listApplications(controller.signal))
      .then(async (items) => {
        if (controller.signal.aborted) return;
        const interviewLists = await Promise.all(items.map((item) => listInterviews(item.entity_id, controller.signal).catch(() => [])));
        setApplications(items);
        setInterviews(interviewLists.flat());
      })
      .catch((caught) => { if (!controller.signal.aborted) setError(localizedApiError(caught)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  const upcoming = useMemo(
    () => interviews.filter((item) => item.status === "scheduled").sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at)),
    [interviews],
  );

  return (
    <main className="page page--wide">
      <PageHeader eyebrow="求职流程" title="申请看板与面试日历" description="状态来自 Career Core；页面只读取现有申请和面试记录。" />
      {error && <Surface><Section title="申请数据" icon={ClipboardList}><ErrorState compact title="暂时无法读取申请" detail={error} /></Section></Surface>}
      {loading && <Surface><Section title="申请数据" icon={ClipboardList}><LoadingState label="正在读取申请和面试…" /></Section></Surface>}
      {!loading && !error && applications.length === 0 && <Surface><Section title="申请看板" icon={ClipboardList}><EmptyState icon={ClipboardList} title="还没有申请记录" description="从机会详情创建准备中的申请后，会在这里按状态显示。" /></Section></Surface>}
      {!loading && !error && applications.length > 0 && <>
        <section className="kanban-board" aria-label="申请状态看板">
          {columns.map((column) => {
            const items = applications.filter((item) => item.state === column.state);
            return <section className="kanban-column" key={column.state} aria-label={column.label}>
              <header><strong>{column.label}</strong><span>{items.length}</span></header>
              {items.length === 0 ? <p className="text-aux">暂无申请</p> : items.map((item) => <article className="kanban-card" key={`${item.entity_id}:${item.revision}`}>
                <strong>{item.entity_id}</strong>
                <p>机会：{item.opportunity_id}</p>
                <p>简历：{item.resume_revision_id ?? "尚未关联"}</p>
                <small>版本 {item.revision} · {item.submitted_at ? dateLabel(item.submitted_at) : "尚未投递"}</small>
              </article>)}
            </section>;
          })}
        </section>
        <Surface>
          <Section title="面试日历" icon={CalendarDays} description="按本机时区显示已安排轮次；点击信息可回到申请标识。" meta={`${upcoming.length} 场待进行`}>
            {upcoming.length === 0 ? <p className="text-aux">暂无已安排面试。</p> : <div className="calendar-list" aria-label="已安排面试">
              {upcoming.map((item) => <article className="calendar-list__item" key={`${item.entity_id}:${item.revision}`}>
                <CalendarDays size={17} aria-hidden="true" />
                <div><strong>{dateLabel(item.scheduled_at)}</strong><p>{item.round} · 申请 {item.application_id} · 申请版本 {item.application_revision}</p></div>
                <span className="badge"><Clock3 size={13} aria-hidden="true" />已安排</span>
              </article>)}
            </div>}
          </Section>
        </Surface>
      </>}
    </main>
  );
}
