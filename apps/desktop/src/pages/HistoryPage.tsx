import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { createInterviewFeedbackProposal, createInterviewPrepProposal, createOfferPreparationProposal, createRejectionPatternProposal, listApplications, listInterviews, listOutcomes } from "../api/history";
import type { ApplicationRead, ApplicationState, InterviewRead, OutcomeRead } from "../api/history";
import { actorLabels, displayLabel } from "../app/displayLabels";
import { getDemoStory } from "../api/demoStory";
import type { DemoStory } from "../api/demoStory";
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
const message = (error: unknown) => error instanceof ApiError ? error.message : "暂时无法读取 Core";

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
    <section className="today-panel history-outcomes" aria-labelledby="outcomes-title">
      <h2 id="outcomes-title" className="today-section-title"><span />已记录的结果</h2>
      <p>结果保留当时的申请修订与来源，不从当前阶段推断。</p>
      {state.status === "loading" && <p role="status">正在读取历史结果…</p>}
      {state.status === "error" && <div role="alert"><p>{state.message}</p><button type="button" onClick={() => setAttempt((n) => n + 1)}>重试结果</button></div>}
      {state.status === "ready" && state.data.length === 0 && <p>这份申请尚无已记录的结果。</p>}
      {state.status === "ready" && state.data.map((outcome) => (
        <article className="history-record" key={outcome.entity_id}>
          <h3>{results[outcome.result]}</h3>
          <dl>
            <dt>发生时间（原始记录）</dt><dd><time>{outcome.occurred_at}</time></dd>
            <dt>来源权威</dt><dd>{outcome.authority === "user_confirmed" ? "用户确认" : "门户回执"}</dd>
            <dt>当时的申请</dt><dd>{outcome.application_id}#{outcome.application_revision}</dd>
            <dt>结果记录</dt><dd>{outcome.entity_id}#{outcome.revision}</dd>
            <dt>记录者</dt><dd>{displayLabel(outcome.recorded_by, actorLabels)}</dd>
            <dt>证据引用</dt><dd>{outcome.evidence_refs.length ? outcome.evidence_refs.join("、") : "无证据引用（用户确认）"}</dd>
          </dl>
        </article>
      ))}
      {state.status === "ready" && state.data.some((outcome) => outcome.result === "offer") && <button type="button" onClick={() => void offerPreparation()}>生成 Offer 准备清单</button>}
      {state.status === "ready" && state.data.some((outcome) => outcome.result === "rejection") && <button type="button" onClick={() => void rejectionPattern()}>分析投递结果模式</button>}
      {insightMessage && <p role="status">{insightMessage}</p>}
    </section>
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
  return <section className="today-panel history-outcomes" aria-labelledby="interview-prep-title">
    <h2 id="interview-prep-title" className="today-section-title"><span />面试准备</h2>
    <p>只基于已有证据生成草稿，不会自动补全经历或发送内容。</p>
    {message && <p role="status">{message}</p>}
    {interviews.length === 0 && !message && <p>这份申请暂无可用面试记录。</p>}
    {interviews.map((interview) => <article className="history-record" key={interview.entity_id}>
      <h3>{interview.round === "technical" ? "技术面试" : "面试"} · {interview.status === "completed" ? "已完成" : interview.status === "scheduled" ? "已安排" : "已取消"}</h3>
      <p><time>{interview.scheduled_at}</time> · 证据 {interview.evidence_refs.length} 条</p>
      <button type="button" onClick={() => void prepare(interview)} disabled={!interview.evidence_refs.length}>生成准备草稿</button>
      {interview.status === "completed" && <>
        <label htmlFor={`interview-answer-${interview.entity_id}`}>记录本次回答（仅生成复盘提案）</label>
        <textarea id={`interview-answer-${interview.entity_id}`} value={answers[interview.entity_id] ?? ""} onChange={(event) => setAnswers((current) => ({ ...current, [interview.entity_id]: event.target.value }))} placeholder="写下你的回答，未知内容保持待确认" />
        <button type="button" onClick={() => void submitFeedback(interview)} disabled={!answers[interview.entity_id]?.trim() || !interview.evidence_refs.length}>生成复盘草稿</button>
      </>}
    </article>)}
  </section>;
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
    <main className="page history-page">
      <header className="page-heading"><div><p className="eyebrow">职业历史</p><h1>职业历程</h1><p>回看已记录的申请与结果。</p><Link to="/history/evidence">查看证据来源</Link></div></header>
      {state.status === "loading" && <p role="status">正在读取申请记录…</p>}
      {state.status === "error" && <div className="today-panel" role="alert"><p>{state.message}</p><button type="button" onClick={() => setAttempt((n) => n + 1)}>重试申请</button></div>}
      {state.status === "ready" && state.data.length === 0 && <section className="today-panel empty-state"><h2>还没有申请记录</h2><p>在 Core 中记录申请后，这里会显示真实进展。</p></section>}
      {demoStory?.available && <section className="today-panel history-story" aria-labelledby="demo-story-title">
        <p className="eyebrow">演示闭环</p>
        <h2 id="demo-story-title">从岗位到面试复盘</h2>
        <p>以下步骤来自隔离 Demo 数据库的已保存记录，刷新后会重新读取。</p>
        <p>岗位评分 {demoStory.score == null ? "待确认" : `${Math.round(demoStory.score * 100)} 分`} · JD 要求 {demoStory.requirements?.length ?? 0} 条 · 证据 {demoStory.evidence_ref_id ?? "尚未建立关联"} · 能力差距 {demoStory.gaps?.length ? demoStory.gaps.join("、") : "暂无"}</p>
        <p>目标简历修改：{demoStory.resume_patch ? `${demoStory.resume_patch.patch_id} · ${demoStory.resume_patch.status === "proposed" ? "待人工审核" : demoStory.resume_patch.status === "accepted" ? "已接受" : "已拒绝"}` : "尚未建立关联"}</p>
        <ol className="history-story-steps">
          {demoStory.steps.map((step) => <li key={step.key} data-status={step.status === "尚未建立关联" ? "pending" : "done"}><span>{step.label}</span><small>{step.status}</small></li>)}
        </ol>
        <div className="history-story-links"><strong>可追溯关联</strong>{demoStory.links.map((link) => <span key={`${link.kind}-${link.id}`}>{link.kind} · {link.label}</span>)}</div>
      </section>}
      {application && <>
        <section className="today-panel history-application">
          <label htmlFor="history-application">选择申请</label>
          <select id="history-application" value={selected} onChange={(event) => setSelected(event.target.value)}>
            {state.status === "ready" && state.data.map((item) => <option value={item.entity_id} key={item.entity_id}>{item.entity_id} · {states[item.state]}</option>)}
          </select>
          <h2>当前阶段：{states[application.state]}</h2>
          <p>申请 {application.entity_id}#{application.revision}</p>
          <p>机会 {application.opportunity_id}#{application.opportunity_revision}</p>
          <p>简历修订 {application.resume_revision_id ?? "未关联"}</p>
          <p>投递时间 {application.submitted_at ?? "未记录"}</p>
        </section>
        <OutcomePanel key={application.entity_id} applicationId={application.entity_id} />
        <InterviewPrepPanel key={`${application.entity_id}-interviews`} applicationId={application.entity_id} />
      </>}
    </main>
  );
}
