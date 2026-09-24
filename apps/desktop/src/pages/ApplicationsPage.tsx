import { CalendarDays, ClipboardList, Clock3 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { attachResumeToApplication, cancelInterview, completeInterview, listApplications, listInterviews, rescheduleInterview, scheduleInterview, setApplicationPreparationState, submitApplication, type ApplicationRead, type InterviewRead } from "../api/history";
import { listResumeBases, listResumeRevisions, type ResumeRevisionRead } from "../api/projectResume";
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
  const [resumeRevisions, setResumeRevisions] = useState<ResumeRevisionRead[]>([]);
  const [selectedResume, setSelectedResume] = useState<Record<string, string>>({});
  const [actionMessage, setActionMessage] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [interviewDrafts, setInterviewDrafts] = useState<Record<string, { round: InterviewRead["round"]; scheduled_at: string }>>({});
  const [rescheduleDrafts, setRescheduleDrafts] = useState<Record<string, string>>({});

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    Promise.resolve(listApplications(controller.signal))
      .then(async (items) => {
        if (controller.signal.aborted) return;
        const interviewLists = await Promise.all(items.map((item) => listInterviews(item.entity_id, controller.signal).catch(() => [])));
        const bases = await listResumeBases(controller.signal).catch(() => []);
        const revisions = (await Promise.all(bases.map((base) => listResumeRevisions(base.resume_id, controller.signal).catch(() => [])))).flat();
        setApplications(items);
        setInterviews(interviewLists.flat());
        setResumeRevisions(revisions);
      })
      .catch((caught) => { if (!controller.signal.aborted) setError(localizedApiError(caught)); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, []);

  const upcoming = useMemo(
    () => [...interviews].sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at)),
    [interviews],
  );

  function updateApplication(updated: ApplicationRead) {
    setApplications((current) => current.map((item) => item.entity_id === updated.entity_id ? updated : item));
  }

  async function attachResume(item: ApplicationRead) {
    const resumeRevisionId = selectedResume[item.entity_id];
    if (!resumeRevisionId) return;
    setBusy(item.entity_id);
    try {
      updateApplication(await attachResumeToApplication(item.entity_id, { command_id: `command_attach_${item.entity_id}_${item.revision}`, expected_revision: item.revision, resume_revision_id: resumeRevisionId }));
      setActionMessage((current) => ({ ...current, [item.entity_id]: "已关联简历版本；仍需你确认进入待投递状态。" }));
    } catch (caught) { setActionMessage((current) => ({ ...current, [item.entity_id]: localizedApiError(caught) })); }
    finally { setBusy(null); }
  }

  async function markReady(item: ApplicationRead) {
    setBusy(item.entity_id);
    try {
      updateApplication(await setApplicationPreparationState(item.entity_id, { command_id: `command_ready_${item.entity_id}_${item.revision}`, expected_revision: item.revision, state: "ready_for_review" }));
      setActionMessage((current) => ({ ...current, [item.entity_id]: "已进入待本人确认；不会自动投递。" }));
    } catch (caught) { setActionMessage((current) => ({ ...current, [item.entity_id]: localizedApiError(caught) })); }
    finally { setBusy(null); }
  }

  async function confirmSubmission(item: ApplicationRead) {
    if (!item.resume_revision_id) return;
    setBusy(item.entity_id);
    try {
      updateApplication(await submitApplication(item.entity_id, { command_id: `command_submit_${item.entity_id}_${item.revision}`, expected_revision: item.revision, resume_revision_id: item.resume_revision_id }));
      setActionMessage((current) => ({ ...current, [item.entity_id]: "已记录本人确认投递；系统未替你发送或提交外部表单。" }));
    } catch (caught) { setActionMessage((current) => ({ ...current, [item.entity_id]: localizedApiError(caught) })); }
    finally { setBusy(null); }
  }

  async function createInterview(item: ApplicationRead) {
    const draft = interviewDrafts[item.entity_id];
    if (!draft?.scheduled_at) return;
    setBusy(`interview:${item.entity_id}`);
    try {
      const created = await scheduleInterview({ command_id: `command_interview_${item.entity_id}_${Date.now()}`, interview_id: `interview_${item.entity_id}_${Date.now()}`, application_id: item.entity_id, application_revision: item.revision, round: draft.round, scheduled_at: new Date(draft.scheduled_at).toISOString() });
      setInterviews((current) => [...current, created]);
      setActionMessage((current) => ({ ...current, [item.entity_id]: "面试轮次已安排并写入本地日历。" }));
    } catch (caught) { setActionMessage((current) => ({ ...current, [item.entity_id]: localizedApiError(caught) })); }
    finally { setBusy(null); }
  }

  function updateInterview(updated: InterviewRead) {
    setInterviews((current) => current.map((item) => item.entity_id === updated.entity_id ? updated : item));
  }

  async function transitionInterview(item: InterviewRead, action: "complete" | "cancel") {
    setBusy(`interview-action:${item.entity_id}`);
    try {
      const updated = action === "complete"
        ? await completeInterview(item.entity_id, { command_id: `command_complete_${item.entity_id}_${item.revision}`, expected_revision: item.revision })
        : await cancelInterview(item.entity_id, { command_id: `command_cancel_${item.entity_id}_${item.revision}`, expected_revision: item.revision });
      updateInterview(updated);
      setActionMessage((current) => ({ ...current, [item.application_id]: action === "complete" ? "面试已标记为完成。" : "面试已取消。" }));
    } catch (caught) { setActionMessage((current) => ({ ...current, [item.application_id]: localizedApiError(caught) })); }
    finally { setBusy(null); }
  }

  async function reschedule(item: InterviewRead) {
    const value = rescheduleDrafts[item.entity_id];
    if (!value) return;
    setBusy(`interview-action:${item.entity_id}`);
    try {
      const updated = await rescheduleInterview(item.entity_id, { command_id: `command_reschedule_${item.entity_id}_${item.revision}`, expected_revision: item.revision, scheduled_at: new Date(value).toISOString() });
      updateInterview(updated);
      setRescheduleDrafts((current) => ({ ...current, [item.entity_id]: "" }));
      setActionMessage((current) => ({ ...current, [item.application_id]: "面试时间已更新。" }));
    } catch (caught) { setActionMessage((current) => ({ ...current, [item.application_id]: localizedApiError(caught) })); }
    finally { setBusy(null); }
  }

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
                {item.state === "preparing" && <div className="application-actions"><select className="select" aria-label={`选择 ${item.entity_id} 的简历版本`} value={selectedResume[item.entity_id] ?? ""} onChange={(event) => setSelectedResume((current) => ({ ...current, [item.entity_id]: event.target.value }))}><option value="">选择简历版本</option>{resumeRevisions.map((revision) => <option key={revision.revision_id} value={revision.revision_id}>{revision.revision_id}</option>)}</select><button className="btn btn--secondary" type="button" disabled={!selectedResume[item.entity_id] || busy === item.entity_id} onClick={() => void attachResume(item)}>关联简历</button>{item.resume_revision_id && <button className="btn btn--primary" type="button" disabled={busy === item.entity_id} onClick={() => void markReady(item)}>进入待本人确认</button>}</div>}
                {item.state === "ready_for_review" && <button className="btn btn--primary" type="button" disabled={busy === item.entity_id || !item.resume_revision_id} onClick={() => void confirmSubmission(item)}>本人确认投递</button>}
                {(item.state === "submitted_by_user" || item.state === "screen" || item.state === "oa" || item.state === "interview") && <div className="application-actions"><select className="select" aria-label={`选择 ${item.entity_id} 的面试轮次`} value={interviewDrafts[item.entity_id]?.round ?? "technical"} onChange={(event) => setInterviewDrafts((current) => ({ ...current, [item.entity_id]: { round: event.target.value as InterviewRead["round"], scheduled_at: current[item.entity_id]?.scheduled_at ?? "" } }))}><option value="screen">初筛</option><option value="technical">技术面</option><option value="loop">综合面</option><option value="offer_talk">Offer 沟通</option></select><input className="input" type="datetime-local" aria-label={`填写 ${item.entity_id} 的面试时间`} value={interviewDrafts[item.entity_id]?.scheduled_at ?? ""} onChange={(event) => setInterviewDrafts((current) => ({ ...current, [item.entity_id]: { round: current[item.entity_id]?.round ?? "technical", scheduled_at: event.target.value } }))} /><button className="btn btn--secondary" type="button" disabled={!interviewDrafts[item.entity_id]?.scheduled_at || busy === `interview:${item.entity_id}`} onClick={() => void createInterview(item)}>安排面试</button></div>}
                {actionMessage[item.entity_id] && <p className="text-aux" role="status">{actionMessage[item.entity_id]}</p>}
              </article>)}
            </section>;
          })}
        </section>
        <Surface>
          <Section title="面试日历" icon={CalendarDays} description="按本机时区显示面试轮次；完成、取消和改期都会保留新的记录版本。" meta={`${upcoming.filter((item) => item.status === "scheduled").length} 场待进行`}>
            {upcoming.length === 0 ? <p className="text-aux">暂无已安排面试。</p> : <div className="calendar-list" aria-label="已安排面试">
              {upcoming.map((item) => <article className="calendar-list__item" key={`${item.entity_id}:${item.revision}`}>
                <CalendarDays size={17} aria-hidden="true" />
                <div><strong>{dateLabel(item.scheduled_at)}</strong><p>{item.round} · 申请 {item.application_id} · 申请版本 {item.application_revision}</p>{item.status === "scheduled" && <div className="application-actions"><input className="input" type="datetime-local" aria-label={`改期 ${item.entity_id}`} value={rescheduleDrafts[item.entity_id] ?? ""} onChange={(event) => setRescheduleDrafts((current) => ({ ...current, [item.entity_id]: event.target.value }))} /><button className="btn btn--secondary" type="button" disabled={!rescheduleDrafts[item.entity_id] || busy === `interview-action:${item.entity_id}`} onClick={() => void reschedule(item)}>改期</button><button className="btn btn--secondary" type="button" disabled={busy === `interview-action:${item.entity_id}`} onClick={() => void transitionInterview(item, "complete")}>完成</button><button className="btn btn--secondary" type="button" disabled={busy === `interview-action:${item.entity_id}`} onClick={() => void transitionInterview(item, "cancel")}>取消</button></div>}</div>
                <span className="badge"><Clock3 size={13} aria-hidden="true" />{item.status === "scheduled" ? "已安排" : item.status === "completed" ? "已完成" : "已取消"}</span>
              </article>)}
            </div>}
          </Section>
        </Surface>
      </>}
    </main>
  );
}
