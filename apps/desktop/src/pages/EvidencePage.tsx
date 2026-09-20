import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ApiError } from "../api/client";
import { getEvidence, listEvidence } from "../api/evidence";
import type { EvidencePageRead, EvidenceProvenance } from "../api/evidence";
import "./EvidencePage.css";

type Load<T> = { status: "loading" } | { status: "error"; message: string }
  | { status: "ready"; data: T };
const message = (error: unknown) => error instanceof ApiError && error.status === 404
  ? "这条证据引用不存在。" : "暂时无法读取证据来源，请检查本地 Core 后重试。";
const sourceLabel = (item: EvidenceProvenance) => item.source.source_type === "legacy_historical_unconfirmed"
  ? "历史来源 · 未确认" : item.source.source_type;
const classes = { public_source: "公开来源", personal: "个人材料", sensitive: "敏感材料" };

function EvidenceDetail({ refId }: { refId: string }) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<Load<EvidenceProvenance>>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    getEvidence(refId, controller.signal).then((data) => {
      if (!controller.signal.aborted) setState({ status: "ready", data });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ status: "error", message: message(error) });
    });
    return () => controller.abort();
  }, [refId, attempt]);
  const item = state.status === "ready" ? state.data : null;
  return <section className="today-panel evidence-detail" aria-label="证据详情">
    <h2 className="today-section-title"><span />来源与快照</h2>
    {state.status === "loading" && <p role="status">正在读取完整来源链…</p>}
    {state.status === "error" && <div role="alert"><p>{state.message}</p><button type="button" onClick={() => setAttempt((n) => n + 1)}>重试详情</button></div>}
    {item && <>
      <p className="evidence-authority">{sourceLabel(item)} · 保存材料不代表确认其中的主张。</p>
      <dl>
        <dt>证据引用</dt><dd>{item.evidence_ref.evidence_ref_id}</dd>
        <dt>来源类型</dt><dd>{item.source.source_type}</dd>
        <dt>来源标识</dt><dd>{item.source.source_id}</dd>
        <dt>历史位置（仅描述）</dt><dd>{item.source.locator}</dd>
        <dt>快照</dt><dd>{item.snapshot.snapshot_id}</dd>
        <dt>采集时间（原始记录）</dt><dd><time>{item.snapshot.captured_at}</time></dd>
        <dt>制品</dt><dd>{item.artifact.artifact_id}</dd>
        <dt>SHA-256</dt><dd>{item.artifact.sha256}</dd>
        <dt>大小</dt><dd>{item.artifact.byte_length.toLocaleString()} bytes</dd>
        <dt>材料分类</dt><dd>{classes[item.artifact.artifact_class]}</dd>
        <dt>媒体类型</dt><dd>{item.artifact.media_type}</dd>
        <dt>精确选择器</dt><dd>{item.evidence_ref.selector ?? "未指定"}</dd>
      </dl>
    </>}
  </section>;
}

export function EvidencePage() {
  const [cursor, setCursor] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<Load<EvidencePageRead>>({ status: "loading" });
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    listEvidence(cursor, controller.signal).then((data) => {
      if (!controller.signal.aborted) setState({ status: "ready", data });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ status: "error", message: message(error) });
    });
    return () => controller.abort();
  }, [cursor, attempt]);
  function navigate(next: string | null) { setSelected(null); setCursor(next); }
  return <main className="page evidence-page">
    <header className="page-heading"><div><p className="eyebrow">History / Evidence</p><h1>证据来源</h1><p>回看已保存材料的来源与精确引用。</p><Link to="/history">返回职业历程</Link></div></header>
    <section className="today-panel evidence-notice"><p>这里显示当前连接的 Core 记录。演练环境与正式环境分别读取，不会自动合并。</p><p>证据保存不等于事实确认，也不代表个人能力已掌握。</p></section>
    {state.status === "loading" && <p role="status">正在读取证据记录…</p>}
    {state.status === "error" && <div className="today-panel" role="alert"><p>{state.message}</p><button type="button" onClick={() => setAttempt((n) => n + 1)}>重试列表</button></div>}
    {state.status === "ready" && <section className="today-panel evidence-list" aria-label="证据列表">
      <h2 className="today-section-title"><span />本页 {state.data.items.length} 条记录</h2>
      {state.data.items.length === 0 && <p>{cursor === null ? "还没有证据记录。" : "此页没有更多证据记录。"}</p>}
      {state.data.items.map((item) => <button className="evidence-item" type="button" key={item.evidence_ref.evidence_ref_id} aria-pressed={selected === item.evidence_ref.evidence_ref_id} onClick={() => setSelected(item.evidence_ref.evidence_ref_id)}>
        <strong>{sourceLabel(item)}</strong><span>{item.evidence_ref.evidence_ref_id}</span><small>{classes[item.artifact.artifact_class]} · {item.artifact.byte_length.toLocaleString()} bytes</small>
      </button>)}
      <div className="evidence-pagination">
        {cursor !== null && <button type="button" onClick={() => navigate(null)}>返回首页</button>}
        {state.data.next_cursor !== null ? <button type="button" onClick={() => navigate(state.data.next_cursor)}>下一页</button> : <p>已到当前记录末尾。</p>}
      </div>
    </section>}
    {selected && <EvidenceDetail key={selected} refId={selected} />}
  </main>;
}
