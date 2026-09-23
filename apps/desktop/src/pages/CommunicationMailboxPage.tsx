import { Mail, RefreshCw, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { getCommunicationSummary, listCommunicationDrafts, reviewCommunicationDraft, transitionCommunicationDraft, type CommunicationDraft, type CommunicationSummary } from "../api/communications";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { ErrorNotice, InlineNotice } from "../components/ui/Notice";

export function CommunicationMailboxPage() {
  const [drafts, setDrafts] = useState<CommunicationDraft[]>([]);
  const [summary, setSummary] = useState<CommunicationSummary | null>(null);
  const [reasons, setReasons] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    setError("");
    Promise.all([listCommunicationDrafts(), getCommunicationSummary()]).then(([items, nextSummary]) => {
      if (!active) return;
      setDrafts(items);
      setSummary(nextSummary);
    }).catch(() => { if (active) setError("求职沟通草稿暂时无法读取，请检查本地服务后重试。"); });
    return () => { active = false; };
  }, [attempt]);

  async function review(draft: CommunicationDraft, decision: "approved" | "rejected") {
    const reason = reasons[draft.draft_id]?.trim();
    if (!reason) return;
    try {
      await reviewCommunicationDraft(draft.draft_id, decision, reason);
      setMessage(decision === "approved" ? "草稿已批准；仍需你在邮件客户端内最终点击发送。" : "草稿已拒绝，未发送任何消息。");
      setAttempt((value) => value + 1);
    } catch { setError("草稿审核失败，请重试。"); }
  }

  async function openApproved(draft: CommunicationDraft) {
    if (draft.status !== "approved") return;
    const subject = encodeURIComponent(`求职沟通 · ${draft.opportunity_id}`);
    window.location.href = `mailto:${encodeURIComponent(draft.recipient ?? "")}?subject=${subject}&body=${encodeURIComponent(draft.body)}`;
    try { await transitionCommunicationDraft(draft.draft_id, "follow_up"); } catch { /* opening the local draft remains safe if state recording fails */ }
  }

  return (
    <main className="page page--wide">
      <PageHeader eyebrow="求职沟通邮箱" title="沟通草稿" description="安全查看、审核并打开单封草稿；观复不会自动读取或发送邮件。" actions={<Button variant="secondary" onClick={() => setAttempt((value) => value + 1)} icon={<RefreshCw size={14} aria-hidden="true" />}>刷新</Button>} />
      {error && <ErrorNotice label="沟通邮箱不可用" detail={error} />}
      {message && <InlineNotice tone="success" role="status">{message}</InlineNotice>}
      <Surface>
        <Section title="连接边界" icon={ShieldCheck} description="当前版本只管理本地草稿，不保存邮箱密码，不后台连接邮箱，不执行批量发送。">
          <div className="metrics-strip" aria-label="沟通概况"><div><span>今日草稿</span><strong>{summary?.created_today ?? "—"}</strong></div><div><span>剩余额度</span><strong>{summary?.remaining_today ?? "—"}</strong></div><div><span>待确认</span><strong>{summary?.counts.pending_review ?? 0}</strong></div></div>
        </Section>
        <Section title="逐封确认" icon={Mail} description="每封草稿都显示岗位、收件人、正文和人工审核理由。">
          {drafts.length === 0 ? <p className="text-aux">还没有沟通草稿。</p> : <div className="record-list">{drafts.map((draft) => <article className="record-list__item" key={draft.draft_id}><div><strong>{draft.draft_id}</strong><p className="text-aux">岗位：{draft.opportunity_id} · 状态：{draft.status}</p><p className="text-aux">收件人：{draft.recipient || "未填写"}</p><pre className="resume-diff">{draft.body}</pre></div>{draft.status === "pending_review" ? <div className="analysis-form"><Field label="审核理由"><input className="input" aria-label={`审核理由 ${draft.draft_id}`} value={reasons[draft.draft_id] || ""} onChange={(event) => setReasons((current) => ({ ...current, [draft.draft_id]: event.target.value }))} /></Field><div className="button-row"><Button variant="secondary" onClick={() => void review(draft, "rejected")} disabled={!reasons[draft.draft_id]?.trim()}>拒绝</Button><Button variant="primary" onClick={() => void review(draft, "approved")} disabled={!reasons[draft.draft_id]?.trim()}>批准</Button></div></div> : draft.status === "approved" ? <Button variant="secondary" onClick={() => void openApproved(draft)}>打开邮件草稿</Button> : null}</article>)}</div>}
        </Section>
      </Surface>
    </main>
  );
}
