import { CalendarDays, ClipboardList, Clock3 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { advanceApplicationState, attachResumeToApplication, cancelInterview, completeInterview, createInterviewFeedbackProposal, createInterviewLearningPlanProposal, createInterviewPrepProposal, listApplications, listInterviews, rescheduleInterview, reviewInterviewProposal, scheduleInterview, setApplicationPreparationState, submitApplication, type ApplicationRead, type ApplicationState, type InterviewProposalRead, type InterviewRead } from "../api/history";
import { downloadInterviewCalendar } from "../api/calendar";
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

function dayKey(value: Date): string {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
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
  const [draggedApplicationId, setDraggedApplicationId] = useState<string | null>(null);
  const [calendarMode, setCalendarMode] = useState<"agenda" | "month">("agenda");
  const [calendarMonth, setCalendarMonth] = useState(() => new Date());
  const [focusedInterviewId, setFocusedInterviewId] = useState<string | null>(null);
  const [prepDrafts, setPrepDrafts] = useState<Record<string, { mode: "technical" | "behavioral"; focus: string }>>({});
  const [feedbackDrafts, setFeedbackDrafts] = useState<Record<string, { question: string; answer: string }>>({});
  const [learningDrafts, setLearningDrafts] = useState<Record<string, string>>({});
  const [interviewProposals, setInterviewProposals] = useState<Record<string, InterviewProposalRead>>({});

  function exportCalendar() {
    try {
      downloadInterviewCalendar(interviews);
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "日历导出失败");
    }
  }

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

  const monthCells = useMemo(() => {
    const first = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), 1);
    const start = new Date(first);
    start.setDate(first.getDate() - first.getDay());
    return Array.from({ length: 42 }, (_, index) => {
      const date = new Date(start);
      date.setDate(start.getDate() + index);
      return date;
    });
  }, [calendarMonth]);

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

  async function moveApplication(item: ApplicationRead, target: ApplicationState) {
    if (item.state === target) return;
    setBusy(`move:${item.entity_id}`);
    try {
      const updated = item.state === "preparing" || item.state === "ready_for_review"
        ? await setApplicationPreparationState(item.entity_id, { command_id: `command_drag_${item.entity_id}_${item.revision}`, expected_revision: item.revision, state: target as "preparing" | "ready_for_review" })
        : await advanceApplicationState(item.entity_id, { command_id: `command_drag_${item.entity_id}_${item.revision}`, expected_revision: item.revision, state: target as Exclude<ApplicationState, "preparing" | "ready_for_review"> });
      updateApplication(updated);
      setActionMessage((current) => ({ ...current, [item.entity_id]: `已将申请移到“${columns.find((column) => column.state === target)?.label ?? target}”。` }));
    } catch (caught) {
      setActionMessage((current) => ({ ...current, [item.entity_id]: localizedApiError(caught) }));
    } finally {
      setBusy(null);
      setDraggedApplicationId(null);
    }
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

  function focusInterview(interviewId: string) {
    setFocusedInterviewId(interviewId);
    setCalendarMode("agenda");
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

  async function createPrep(item: InterviewRead) {
    const draft = prepDrafts[item.entity_id] ?? { mode: "behavioral", focus: "" };
    setBusy(`prep:${item.entity_id}`);
    try {
      const proposal = await createInterviewPrepProposal(item.entity_id, draft);
      setInterviewProposals((current) => ({ ...current, [item.entity_id]: proposal }));
      setActionMessage((current) => ({ ...current, [item.application_id]: "面试准备提案已生成，等待你审核。" }));
    } catch (caught) { setActionMessage((current) => ({ ...current, [item.application_id]: localizedApiError(caught) })); }
    finally { setBusy(null); }
  }

  async function createFeedback(item: InterviewRead) {
    const draft = feedbackDrafts[item.entity_id];
    if (!draft?.answer.trim()) return;
    setBusy(`feedback:${item.entity_id}`);
    try {
      const proposal = await createInterviewFeedbackProposal(item.entity_id, draft);
      setInterviewProposals((current) => ({ ...current, [item.entity_id]: proposal }));
      setActionMessage((current) => ({ ...current, [item.application_id]: "面试复盘提案已生成，未写入职业事实。" }));
    } catch (caught) { setActionMessage((current) => ({ ...current, [item.application_id]: localizedApiError(caught) })); }
    finally { setBusy(null); }
  }

  async function createLearningPlan(item: InterviewRead) {
    const gaps = (learningDrafts[item.entity_id] ?? "").split(/[，,\n]/).map((value) => value.trim()).filter(Boolean);
    setBusy(`learning:${item.entity_id}`);
    try {
      const proposal = await createInterviewLearningPlanProposal(item.entity_id, gaps);
      setInterviewProposals((current) => ({ ...current, [item.entity_id]: proposal }));
      setActionMessage((current) => ({ ...current, [item.application_id]: "学习计划提案已生成，批准后才会进入任务队列。" }));
    } catch (caught) { setActionMessage((current) => ({ ...current, [item.application_id]: localizedApiError(caught) })); }
    finally { setBusy(null); }
  }

  async function reviewInterviewProposalFor(item: InterviewRead, decision: "approved" | "rejected") {
    const proposal = interviewProposals[item.entity_id];
    if (!proposal) return;
    setBusy(`proposal:${item.entity_id}`);
    try {
      const reviewed = await reviewInterviewProposal(proposal.proposal_id, decision, decision === "approved" ? "用户核对面试提案内容" : "用户拒绝面试提案内容");
      setInterviewProposals((current) => ({ ...current, [item.entity_id]: reviewed }));
      setActionMessage((current) => ({ ...current, [item.application_id]: decision === "approved" ? "提案已批准；内容仍保留为知识审核结果。" : "提案已拒绝，未修改职业事实。" }));
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
            return <section className="kanban-column" key={column.state} aria-label={column.label} onDragOver={(event) => { event.preventDefault(); }} onDrop={(event) => { event.preventDefault(); const application = applications.find((candidate) => candidate.entity_id === (event.dataTransfer.getData("text/plain") || draggedApplicationId)); if (application) void moveApplication(application, column.state); }}>
              <header><strong>{column.label}</strong><span>{items.length}</span></header>
              {items.length === 0 ? <p className="text-aux">暂无申请</p> : items.map((item) => <article className="kanban-card" draggable={item.state !== "offer" && item.state !== "rejected"} onDragStart={(event) => { setDraggedApplicationId(item.entity_id); event.dataTransfer.setData("text/plain", item.entity_id); }} key={`${item.entity_id}:${item.revision}`}>
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
            {upcoming.length > 0 && <div className="calendar-controls"><div className="button-row"><button className={`btn ${calendarMode === "agenda" ? "btn--primary" : "btn--secondary"}`} type="button" onClick={() => setCalendarMode("agenda")}>列表</button><button className={`btn ${calendarMode === "month" ? "btn--primary" : "btn--secondary"}`} type="button" onClick={() => setCalendarMode("month")}>月视图</button><button className="btn btn--secondary" type="button" onClick={exportCalendar}>导出 .ics</button></div>{calendarMode === "month" && <div className="button-row"><button className="btn btn--secondary" type="button" aria-label="上个月" onClick={() => setCalendarMonth((current) => new Date(current.getFullYear(), current.getMonth() - 1, 1))}>上个月</button><strong aria-live="polite">{calendarMonth.getFullYear()} 年 {calendarMonth.getMonth() + 1} 月</strong><button className="btn btn--secondary" type="button" aria-label="下个月" onClick={() => setCalendarMonth((current) => new Date(current.getFullYear(), current.getMonth() + 1, 1))}>下个月</button></div>}</div>}
            {upcoming.length === 0 ? <p className="text-aux">暂无已安排面试。</p> : <div className="calendar-list" aria-label="已安排面试">
              {calendarMode === "month" ? <div className="calendar-month" aria-label="面试月视图"><div className="calendar-month__weekdays">{["日", "一", "二", "三", "四", "五", "六"].map((day) => <span key={day}>{day}</span>)}</div><div className="calendar-month__grid">{monthCells.map((date) => { const key = dayKey(date); const events = upcoming.filter((item) => dayKey(new Date(item.scheduled_at)) === key); return <div className={`calendar-day ${date.getMonth() === calendarMonth.getMonth() ? "" : "calendar-day--outside"}`} key={key}><time dateTime={key}>{date.getDate()}</time>{events.map((item) => <button className="calendar-day__event" type="button" key={`${item.entity_id}:${item.revision}`} aria-label={`查看 ${item.application_id} 的 ${item.round} 面试`} onClick={() => focusInterview(item.entity_id)}>{item.round} · {new Date(item.scheduled_at).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" })}</button>)}</div>; })}</div></div> : upcoming.map((item) => <article className="calendar-list__item" aria-current={focusedInterviewId === item.entity_id ? "true" : undefined} key={`${item.entity_id}:${item.revision}`}>
                <CalendarDays size={17} aria-hidden="true" />
                <div><strong>{dateLabel(item.scheduled_at)}</strong><p>{item.round} · 申请 {item.application_id} · 申请版本 {item.application_revision}</p>{item.status === "scheduled" && <div className="application-actions"><input className="input" type="datetime-local" aria-label={`改期 ${item.entity_id}`} value={rescheduleDrafts[item.entity_id] ?? ""} onChange={(event) => setRescheduleDrafts((current) => ({ ...current, [item.entity_id]: event.target.value }))} /><button className="btn btn--secondary" type="button" disabled={!rescheduleDrafts[item.entity_id] || busy === `interview-action:${item.entity_id}`} onClick={() => void reschedule(item)}>改期</button><button className="btn btn--secondary" type="button" disabled={busy === `interview-action:${item.entity_id}`} onClick={() => void transitionInterview(item, "complete")}>完成</button><button className="btn btn--secondary" type="button" disabled={busy === `interview-action:${item.entity_id}`} onClick={() => void transitionInterview(item, "cancel")}>取消</button></div>}</div>
                <span className="badge"><Clock3 size={13} aria-hidden="true" />{item.status === "scheduled" ? "已安排" : item.status === "completed" ? "已完成" : "已取消"}</span>
              </article>)}
            </div>}
          </Section>
        </Surface>
        {upcoming.some((item) => item.status === "completed") && <Surface>
          <Section title="面试准备与复盘" icon={ClipboardList} description="规则反馈只生成待审核提案，不会自动写入能力、事实、简历或学习任务。">
            <div className="interview-review-list">
              {upcoming.filter((item) => item.status === "completed").map((item) => {
                const prep = prepDrafts[item.entity_id] ?? { mode: "behavioral" as const, focus: "" };
                const feedback = feedbackDrafts[item.entity_id] ?? { question: "", answer: "" };
                const proposal = interviewProposals[item.entity_id];
                return <article className="interview-review-card" key={item.entity_id} aria-label={`面试复盘 ${item.entity_id}`}>
                  <header><strong>{item.entity_id}</strong><span>{item.round} · 申请 {item.application_id}</span></header>
                  <div className="application-actions"><select className="select" aria-label={`选择 ${item.entity_id} 的准备类型`} value={prep.mode} onChange={(event) => setPrepDrafts((current) => ({ ...current, [item.entity_id]: { ...prep, mode: event.target.value as "technical" | "behavioral" } }))}><option value="behavioral">行为面试</option><option value="technical">技术面试</option></select><input className="input" aria-label={`填写 ${item.entity_id} 的准备重点`} placeholder="准备重点（可选）" value={prep.focus} onChange={(event) => setPrepDrafts((current) => ({ ...current, [item.entity_id]: { ...prep, focus: event.target.value } }))} /><button className="btn btn--secondary" type="button" disabled={busy === `prep:${item.entity_id}`} onClick={() => void createPrep(item)}>生成准备提案</button></div>
                  <label className="field"><span className="field__label">面试题目</span><input className="input" aria-label={`填写 ${item.entity_id} 的面试题目`} value={feedback.question} onChange={(event) => setFeedbackDrafts((current) => ({ ...current, [item.entity_id]: { ...feedback, question: event.target.value } }))} /></label>
                  <label className="field"><span className="field__label">我的回答</span><textarea className="textarea" aria-label={`填写 ${item.entity_id} 的面试回答`} rows={4} value={feedback.answer} onChange={(event) => setFeedbackDrafts((current) => ({ ...current, [item.entity_id]: { ...feedback, answer: event.target.value } }))} /></label>
                  <div className="button-row"><button className="btn btn--primary" type="button" disabled={!feedback.answer.trim() || busy === `feedback:${item.entity_id}`} onClick={() => void createFeedback(item)}>生成复盘提案</button><input className="input" aria-label={`填写 ${item.entity_id} 的学习缺口`} placeholder="学习缺口，用逗号分隔" value={learningDrafts[item.entity_id] ?? ""} onChange={(event) => setLearningDrafts((current) => ({ ...current, [item.entity_id]: event.target.value }))} /><button className="btn btn--secondary" type="button" disabled={busy === `learning:${item.entity_id}`} onClick={() => void createLearningPlan(item)}>生成学习计划</button></div>
                  {proposal && <div className="proposal-review" aria-label={`${item.entity_id} 的面试提案`}><strong>{proposal.title}</strong><span className="badge">{proposal.status === "pending" ? "待审核" : proposal.status === "approved" ? "已批准" : "已拒绝"}</span><pre>{proposal.proposed_content}</pre>{proposal.status === "pending" && <div className="button-row"><button className="btn btn--primary" type="button" disabled={busy === `proposal:${item.entity_id}`} onClick={() => void reviewInterviewProposalFor(item, "approved")}>批准提案</button><button className="btn btn--secondary" type="button" disabled={busy === `proposal:${item.entity_id}`} onClick={() => void reviewInterviewProposalFor(item, "rejected")}>拒绝提案</button></div>}</div>}
                </article>;
              })}
            </div>
          </Section>
        </Surface>}
      </>}
    </main>
  );
}
