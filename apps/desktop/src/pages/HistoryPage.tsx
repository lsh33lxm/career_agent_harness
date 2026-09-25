import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { CircleCheck, FileClock, RotateCcw } from "lucide-react";

import { localizedApiError } from "../api/client";
import { createInterviewFeedbackProposal, createInterviewPrepProposal, createOfferPreparationProposal, createRejectionPatternProposal, listApplications, listInterviews, listOutcomes } from "../api/history";
import type { ApplicationRead, ApplicationState, InterviewRead, OutcomeRead } from "../api/history";
import { actorLabels, displayLabel } from "../app/displayLabels";
import { getDemoStory } from "../api/demoStory";
import type { DemoStory } from "../api/demoStory";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { InlineNotice, StatusBanner } from "../components/ui/Notice";
import "./HistoryPage.css";

const states: Record<ApplicationState, string> = {
  preparing: "准备中", ready_for_review: "待确认", submitted_by_user: "用户已投递",
  screen: "筛选中", oa: "在线测评", interview: "面试中", offer: "录用意向",
  rejected: "未通过", withdrawn: "已撤回", closed: "已关闭",
};
const results: Record<OutcomeRead["result"], string> = {
  offer: "录用意向", rejection: "未通过", withdrawal: "已撤回", closed: "已关闭",
};
type Load<T> = { status: "loading" } | { status: "error"; message: string }
  | { status: "ready"; data: T };
const message = (error: unknown) => localizedApiError(error);

function OutcomePanel({ applicationId }: { applicationId: string }) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<Load<OutcomeRead[]>>({ status: "loading" });
  const [insightMessage, setInsightMessage] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    listOutcomes(applicationId, controller.signal).then((data) => {
      if (!controller.signal.aborted) setState({ status: "ready", data });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ status: "error", message: message(error) });
    });
    return () => controller.abort();
  }, [applicationId, attempt]);
  async function offerPreparation() {
    try {
      const result = await createOfferPreparationProposal(applicationId);
      setInsightMessage(`Offer 准备清单已创建，等待审核：${result.proposal_id}`);
    } catch (error) {
      setInsightMessage(`Offer 准备清单生成失败：${error instanceof Error ? error.message : "未知错误"}`);
    }
  }
  async function rejectionPattern() {
    try {
      const result = await createRejectionPatternProposal();
      setInsightMessage(`投递结果分析已创建，等待审核：${result.proposal_id}`);
    } catch (error) {
      setInsightMessage(`投递结果分析生成失败：${error instanceof Error ? error.message : "未知错误"}`);
    }
  }
  return (
    <Surface>
      <Section title="已记录的结果" description="结果保留当时的申请修订与来源，不从当前阶段推断。">
        {state.status === "loading" && <LoadingState compact label="正在读取历史结果…" />}
        {state.status === "error" && (
          <ErrorState compact title="暂时无法读取历史结果" detail={state.message} onRetry={() => setAttempt((n) => n + 1)} retryLabel="重试结果" />
        )}
        {state.status === "ready" && state.data.length === 0 && <p className="text-aux">这份申请尚无已记录的结果。</p>}
        {state.status === "ready" && state.data.map((outcome) => (
          <article className="history-record" key={outcome.entity_id}>
            <h3>{results[outcome.result]}</h3>
            <dl className="dl">
              <div><dt>发生时间（原始记录）</dt><dd><time>{outcome.occurred_at}</time></dd></div>
              <div><dt>来源权威</dt><dd>{outcome.authority === "user_confirmed" ? "用户确认" : "门户回执"}</dd></div>
              <div><dt>当时的申请</dt><dd>{outcome.application_id}#{outcome.application_revision}</dd></div>
              <div><dt>结果记录</dt><dd>{outcome.entity_id}#{outcome.revision}</dd></div>
              <div><dt>记录者</dt><dd>{displayLabel(outcome.recorded_by, actorLabels)}</dd></div>
              <div><dt>证据引用</dt><dd>{outcome.evidence_refs.length ? outcome.evidence_refs.join("、") : "无证据引用（用户确认）"}</dd></div>
            </dl>
          </article>
        ))}
        {state.status === "ready" && (state.data.some((outcome) => outcome.result === "offer") || state.data.some((outcome) => outcome.result === "rejection")) && (
          <div className="resume-actions" style={{ marginTop: "var(--space-3)" }}>
            {state.data.some((outcome) => outcome.result === "offer") && (
              <Button variant="secondary" onClick={() => void offerPreparation()}>生成 Offer 准备清单</Button>
            )}
            {state.data.some((outcome) => outcome.result === "rejection") && (
              <Button variant="secondary" onClick={() => void rejectionPattern()}>分析投递结果模式</Button>
            )}
          </div>
        )}
        {insightMessage && (
          <div style={{ marginTop: "var(--space-3)" }}>
            <InlineNotice tone={insightMessage.includes("失败") ? "danger" : "success"} role="status">{insightMessage}</InlineNotice>
          </div>
        )}
      </Section>
    </Surface>
  );
}

function InterviewPrepPanel({ applicationId }: { applicationId: string }) {
  const [interviews, setInterviews] = useState<InterviewRead[]>([]);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  useEffect(() => {
    void listInterviews(applicationId).then(setInterviews).catch(() => setMessage("面试记录暂时不可用"));
  }, [applicationId]);
  async function prepare(interview: InterviewRead) {
    try {
      const result = await createInterviewPrepProposal(interview.entity_id, {
        mode: interview.round === "technical" ? "technical" : "behavioral",
        focus: "结合岗位要求和已确认经历准备追问",
      });
      setMessage(`面试准备草稿已创建，等待审核：${result.proposal_id}`);
    } catch (error) {
      setMessage(`面试准备失败：${error instanceof Error ? error.message : "未知错误"}`);
    }
  }
  async function submitFeedback(interview: InterviewRead) {
    try {
      const result = await createInterviewFeedbackProposal(interview.entity_id, {
        question: "",
        answer: answers[interview.entity_id] ?? "",
      });
      setMessage(`面试复盘草稿已创建，等待审核：${result.proposal_id}`);
    } catch (error) {
      setMessage(`面试复盘失败：${error instanceof Error ? error.message : "未知错误"}`);
    }
  }
  return (
    <Surface>
      <Section title="面试准备" description="只基于已有证据生成草稿，不会自动补全经历或发送内容。">
        {message && <InlineNotice tone={message.includes("失败") || message.includes("不可用") ? "danger" : "success"} role="status">{message}</InlineNotice>}
        {interviews.length === 0 && !message && <p className="text-aux">这份申请暂无可用面试记录。</p>}
        {interviews.map((interview) => (
          <article className="history-record" key={interview.entity_id}>
            <h3>{interview.round === "technical" ? "技术面试" : "面试"} · {interview.status === "completed" ? "已完成" : interview.status === "scheduled" ? "已安排" : "已取消"}</h3>
            <p className="text-aux"><time>{interview.scheduled_at}</time> · 证据 {interview.evidence_refs.length} 条</p>
            <div className="resume-actions">
              <Button size="sm" variant="secondary" onClick={() => void prepare(interview)} disabled={!interview.evidence_refs.length}>生成准备草稿</Button>
            </div>
            {interview.status === "completed" && (
              <div className="history-record__feedback">
                <Field label="记录本次回答（仅生成复盘提案）">
                  <textarea
                    className="textarea"
                    id={`interview-answer-${interview.entity_id}`}
                    value={answers[interview.entity_id] ?? ""}
                    onChange={(event) => setAnswers((current) => ({ ...current, [interview.entity_id]: event.target.value }))}
                    placeholder="写下你的回答，未知内容保持待确认"
                  />
                </Field>
                <div>
                  <Button size="sm" variant="secondary" onClick={() => void submitFeedback(interview)} disabled={!answers[interview.entity_id]?.trim() || !interview.evidence_refs.length}>生成复盘草稿</Button>
                </div>
              </div>
            )}
          </article>
        ))}
      </Section>
    </Surface>
  );
}

export function HistoryPage() {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<Load<ApplicationRead[]>>({ status: "loading" });
  const [selected, setSelected] = useState("");
  const [demoStory, setDemoStory] = useState<DemoStory | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    listApplications(controller.signal).then((data) => {
      if (controller.signal.aborted) return;
      setState({ status: "ready", data });
      setSelected((current) => data.some((item) => item.entity_id === current) ? current : data[0]?.entity_id ?? "");
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ status: "error", message: message(error) });
    });
    return () => controller.abort();
  }, [attempt]);
  useEffect(() => {
    const controller = new AbortController();
    getDemoStory(controller.signal).then((value) => {
      if (!controller.signal.aborted) setDemoStory(value);
    }).catch(() => {
      if (!controller.signal.aborted) setDemoStory(null);
    });
    return () => controller.abort();
  }, [attempt]);
  const application = state.status === "ready" ? state.data.find((item) => item.entity_id === selected) : undefined;
  return (
    <main className="page">
      <PageHeader
        eyebrow="职业历史"
        title="职业历程"
        description="回看已记录的申请与结果。"
        actions={<Link className="btn btn--secondary" to="/history/evidence">查看证据来源</Link>}
        art
      />
      {state.status === "loading" && (
        <Surface><Section title="申请记录" icon={FileClock} ariaLabel="申请记录"><LoadingState label="正在读取申请记录…" /></Section></Surface>
      )}
      {state.status === "error" && (
        <Surface>
          <Section title="申请记录" icon={FileClock} ariaLabel="申请记录">
            <StatusBanner tone="warning" title="当前为离线状态，部分最新记录可能未同步。" role="alert"
              actions={<Button size="sm" variant="secondary" onClick={() => setAttempt((n) => n + 1)} icon={<RotateCcw size={13} aria-hidden="true" />}>重试申请</Button>}
            >
              恢复连接后重试即可；已确认的申请与结果不会丢失。
            </StatusBanner>
            <details className="state__details" style={{ marginTop: "var(--space-2)" }}>
              <summary>查看诊断</summary>
              <pre>{state.message}</pre>
            </details>
          </Section>
        </Surface>
      )}
      {state.status === "ready" && state.data.length === 0 && (
        <Surface><Section title="申请记录" icon={FileClock} ariaLabel="申请记录">
          <EmptyState icon={FileClock} title="还没有申请记录" description="在 Core 中记录申请后，这里会显示真实进展。" />
        </Section></Surface>
      )}
      {demoStory?.available && (
        <Surface>
          <Section title="演示闭环" description="从岗位要求与 Evidence 到 Patch 审核、简历版本和申请。">
            <p>记录来自隔离 Demo 数据库，刷新后会重新读取；不代表真实投递。 <Link to="/opportunities">返回岗位</Link> · <Link to="/resume">查看简历</Link> · <Link to="/knowledge">查看知识</Link></p>
            <p>岗位 {demoStory.opportunity_id ?? "尚未建立关联"} · JD 要求 {demoStory.requirements?.length ?? 0} 条 · Evidence {demoStory.evidence_ref_id ?? "尚未建立关联"}</p>
            <div className="history-story-steps">
              {demoStory.steps.map((step) => <div key={step.key} data-status={step.status === "尚未建立关联" ? "pending" : "done"}><strong>{step.label}</strong><span>{step.status}</span></div>)}
            </div>
            <div className="history-story-links">
              {demoStory.resume_patches?.map((patch) => <span key={patch.patch_id}><strong>Patch · {patch.review_status}</strong><small>{patch.patch_id} · {patch.review_source} · {patch.reviewed_at ?? "尚未建立关联"} · {patch.operations.flatMap((op) => op.evidence_ids).join("、") || "尚未建立关联"}</small></span>)}
              {demoStory.links.map((link) => <span key={`${link.kind}-${link.id}`}><strong>{link.kind} · {link.label}</strong><small>{link.id}</small></span>)}
            </div>
            <p>ResumeRevision {demoStory.resume_revision_id ?? "尚未建立关联"} · Application {demoStory.application_id ?? "尚未建立关联"} · 状态 {demoStory.application_state ?? "尚未建立关联"}</p>
          </Section>
        </Surface>
      )}
      {application && (
        <>
          <Surface>
            <div className="metrics-strip" aria-label="申请概况">
              <div><span>申请记录</span><strong>{state.status === "ready" ? state.data.length : 0}</strong></div>
              <div><span>获得面试</span><strong>{state.status === "ready" ? state.data.filter((item) => ["screen", "oa", "interview"].includes(item.state)).length : 0}</strong></div>
              <div><span>收到 Offer</span><strong>{state.status === "ready" ? state.data.filter((item) => item.state === "offer").length : 0}</strong></div>
              <div><span>未通过</span><strong>{state.status === "ready" ? state.data.filter((item) => item.state === "rejected").length : 0}</strong></div>
            </div>
            <Section
              title="申请记录"
              icon={FileClock}
              meta={(
                <Field label="选择申请" className="capability-header-field">
                  <select
                    className="select"
                    id="history-application"
                    value={selected}
                    onChange={(event) => setSelected(event.target.value)}
                  >
                    {state.status === "ready" && state.data.map((item) => <option value={item.entity_id} key={item.entity_id}>{item.entity_id} · {states[item.state]}</option>)}
                  </select>
                </Field>
              )}
            >
              <div className="timeline" role="list" aria-label="申请时间线">
                {state.status === "ready" && state.data.map((item) => (
                  <button
                    type="button"
                    role="listitem"
                    key={item.entity_id}
                    className={`timeline__row${item.entity_id === application.entity_id ? " is-selected" : ""}`}
                    aria-pressed={item.entity_id === application.entity_id}
                    onClick={() => setSelected(item.entity_id)}
                  >
                    <span className={`timeline__dot timeline__dot--${item.state}`} aria-hidden="true" />
                    <span className="timeline__body">
                      <strong>{item.entity_id}</strong>
                      <span className={`badge badge--${item.state === "offer" ? "green" : item.state === "rejected" ? "danger" : item.state === "interview" || item.state === "screen" || item.state === "oa" ? "gold" : ""}`}>{states[item.state]}</span>
                    </span>
                    <span className="timeline__meta">
                      <span>投递时间 {item.submitted_at ?? "未记录"}</span>
                      <span>简历修订 {item.resume_revision_id ?? "未关联"}</span>
                    </span>
                    <Link className="timeline__evidence" to="/history/evidence" onClick={(event) => event.stopPropagation()}>查看证据来源</Link>
                  </button>
                ))}
              </div>
            </Section>
            <Section title="当前阶段" icon={CircleCheck} ariaLabel="当前阶段">
              <div className="history-application__summary">
                <h2>当前阶段：{states[application.state]}</h2>
                <div className="history-application__facts">
                  <p>申请 {application.entity_id}#{application.revision}</p>
                  <p>机会 {application.opportunity_id}#{application.opportunity_revision}</p>
                  <p>简历修订 {application.resume_revision_id ?? "未关联"}</p>
                  <p>投递时间 {application.submitted_at ?? "未记录"}</p>
                </div>
              </div>
            </Section>
          </Surface>
          <OutcomePanel key={application.entity_id} applicationId={application.entity_id} />
          <InterviewPrepPanel key={`${application.entity_id}-interviews`} applicationId={application.entity_id} />
        </>
      )}
    </main>
  );
}
