import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { ApiError } from "../api/client";
import { listApplications, listOutcomes } from "../api/history";
import type { ApplicationRead, ApplicationState, OutcomeRead } from "../api/history";
import { actorLabels, displayLabel } from "../app/displayLabels";
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
    </section>
  );
}

export function HistoryPage() {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<Load<ApplicationRead[]>>({ status: "loading" });
  const [selected, setSelected] = useState("");
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
  const application = state.status === "ready" ? state.data.find((item) => item.entity_id === selected) : undefined;
  return (
    <main className="page history-page">
      <header className="page-heading"><div><p className="eyebrow">职业历史</p><h1>职业历程</h1><p>回看已记录的申请与结果。</p><Link to="/history/evidence">查看证据来源</Link></div></header>
      {state.status === "loading" && <p role="status">正在读取申请记录…</p>}
      {state.status === "error" && <div className="today-panel" role="alert"><p>{state.message}</p><button type="button" onClick={() => setAttempt((n) => n + 1)}>重试申请</button></div>}
      {state.status === "ready" && state.data.length === 0 && <section className="today-panel empty-state"><h2>还没有申请记录</h2><p>在 Core 中记录申请后，这里会显示真实进展。</p></section>}
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
      </>}
    </main>
  );
}
