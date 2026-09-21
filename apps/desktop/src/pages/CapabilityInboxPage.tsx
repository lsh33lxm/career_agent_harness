import { type FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { ApiError } from "../api/client";
import { listCapabilityInbox, reviewCapabilityCandidate, type InboxItem, type InboxReceipt, type InboxReviewRequest } from "../api/capabilityInbox";
import { actorLabels, capabilityLayerLabels, candidateStatusLabels, displayLabel } from "../app/displayLabels";
import "./CapabilityInboxPage.css";

function requestId(prefix: string): string {
  const suffix = globalThis.crypto.randomUUID?.().replaceAll("-", "_")
    ?? `${Date.now()}_${Math.random().toString(36).slice(2)}`;
  return `${prefix}_${suffix}`;
}

function ReviewCard({ item, refresh }: { item: InboxItem; refresh: () => Promise<boolean> }) {
  const { candidate, revision } = item;
  const [decision, setDecision] = useState<"accept" | "reject" | "">("");
  const [reason, setReason] = useState("");
  const [operation, setOperation] = useState<{ request: InboxReviewRequest; key: string } | null>(null);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState("");
  const [conflict, setConflict] = useState(false);
  const [receipt, setReceipt] = useState<InboxReceipt | null>(null);
  const forbidden = candidate.discovered_by === "user";
  const editable = !pending && !receipt && !conflict && candidate.status === "pending" && !forbidden;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!editable || !decision || !reason.trim()) return;
    const submitted = operation ?? {
      request: { command_id: requestId("command"), expected_revision: revision, decision, reason },
      key: requestId("idempotency"),
    };
    setOperation(submitted);
    setPending(true);
    setError("");
    try {
      const result = await reviewCapabilityCandidate(candidate.candidate_node_id, submitted.request, submitted.key);
      setReceipt(result);
      setOperation(null);
      await refresh(); // Read failures are reported by the page, not as mutation failures.
    } catch (failure) {
      if (failure instanceof ApiError && failure.status === 409) {
        setConflict(true);
        setOperation(null);
        setError("审核冲突，请刷新后重新选择决定，不会自动重发。");
      } else {
        setError("未确认审核结果。重试将发送相同请求；修改决定或理由会创建新请求。");
      }
    } finally { setPending(false); }
  }
  return <article className="inbox-card">
    <p>{candidate.status === "pending" ? "待审核" : "审核历史"}</p>
    <h2>{candidate.proposed_canonical_name}</h2>
    <p>{candidate.proposed_description}</p>
    <p>候选编号：{candidate.candidate_node_id} · 第 {revision} 版 · {displayLabel(candidate.status, candidateStatusLabels)}</p>
    <p>发现者：{displayLabel(candidate.discovered_by, actorLabels)} · 层级：{displayLabel(candidate.proposed_layer, capabilityLayerLabels)}</p>
    <p>来源证据：{candidate.source_evidence_refs.join(" · ")}</p>
    {candidate.review_reason && <p>历史审核：{candidate.reviewed_by} — {candidate.review_reason}</p>}
    {forbidden && <p>用户本人提出的候选不能由同一用户审核。</p>}
    {candidate.status === "pending" && <form onSubmit={submit}>
      <label>审核决定<select value={decision} disabled={!editable} onChange={(e) => { setDecision(e.target.value as typeof decision); setOperation(null); }}>
        <option value="">请选择</option><option value="accept">接受：发布新官方图谱</option><option value="reject">忽略：保留审核历史</option>
      </select></label>
      <label>审核理由<textarea value={reason} maxLength={2048} disabled={!editable} onChange={(e) => { setReason(e.target.value); setOperation(null); }} /></label>
      <button disabled={!editable || !decision || !reason.trim()} type="submit">{pending ? "审核中…" : operation ? "重试原审核" : "确认审核"}</button>
    </form>}
    {error && <p role="alert">{error}</p>}
    {conflict && <button disabled={pending} onClick={() => { void refresh().then((ok) => { if (ok) { setConflict(false); setDecision(""); setReason(""); setError(""); } }); }}>刷新审核状态</button>}
    {receipt && <section role="status"><h3>审核已成功</h3><p>回执：{receipt.commit.event_id} · 第 {receipt.commit.revision} 版</p>
      {receipt.capability_id && <p>能力 ID：{receipt.capability_id}</p>}
      {receipt.graph_version && <p>图谱 ID：{receipt.graph_version.graph_version_id}</p>}
    </section>}
  </article>;
}

export function CapabilityInboxPage() {
  const location = useLocation();
  const [items, setItems] = useState<InboxItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [loaded, setLoaded] = useState(false);
  const refresh = useCallback(async () => {
    setLoading(true); setError("");
    try { setItems(await listCapabilityInbox()); setLoaded(true); return true; }
    catch { setError("读取审核列表失败；已确认的审核结果仍然有效。"); return false; }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { void refresh(); }, [refresh]);
  return <main className="capability-inbox"><header><h1>能力候选收件箱</h1><p>候选属于全局能力本体，不表示个人掌握。接受会发布新官方图谱；忽略保留历史。</p><Link to="/capabilities" state={location.state}>返回能力地图</Link></header>
    {loading && <p role="status">正在加载收件箱…</p>}
    {error && <div role="alert">{error}<button disabled={loading} onClick={() => { void refresh(); }}>重试读取</button></div>}
    {loaded && !loading && !items.length && <p>暂无能力候选</p>}
    <section aria-label="候选与审核历史">{items.map((item) => <ReviewCard key={item.candidate.candidate_node_id} item={item} refresh={refresh} />)}</section>
  </main>;
}
