import { Mail, RefreshCw, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { associateMailboxMessage, fetchMailboxMessages, getCommunicationSummary, listCommunicationDrafts, listMailboxAccounts, reviewCommunicationDraft, saveMailboxAccount, testMailboxAccount, transitionCommunicationDraft, type CommunicationDraft, type CommunicationSummary, type MailboxAccount, type MailMessage } from "../api/communications";
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
  const [accounts, setAccounts] = useState<MailboxAccount[]>([]);
  const [messages, setMessages] = useState<MailMessage[]>([]);
  const [association, setAssociation] = useState<Record<string, { opportunity_id: string; application_id: string }>>({});
  const [accountForm, setAccountForm] = useState({ account_id: "mailbox_main", display_name: "主求职邮箱", provider: "自定义 IMAP", username: "", imap_host: "", imap_port: 993, security: "ssl" as "ssl" | "starttls", secret: "" });

  useEffect(() => {
    let active = true;
    setError("");
    Promise.all([listCommunicationDrafts(), getCommunicationSummary(), listMailboxAccounts()]).then(([items, nextSummary, nextAccounts]) => {
      if (!active) return;
      setDrafts(items);
      setSummary(nextSummary);
      setAccounts(nextAccounts);
    }).catch(() => { if (active) setError("求职沟通草稿暂时无法读取，请检查本地服务后重试。"); });
    return () => { active = false; };
  }, [attempt]);

  async function saveAccount() {
    try { const saved = await saveMailboxAccount(accountForm); setAccounts([saved]); setMessage("邮箱配置已保存到安全凭据存储；尚未发起连接。"); }
    catch { setError("邮箱配置未保存，请检查必填项。"); }
  }

  async function testAccount(accountId: string) {
    const result = await testMailboxAccount(accountId);
    setMessage(result.status === "ok" ? "邮箱连接测试通过；观复仍不会自动读取或发送。" : (result.message ?? "连接测试失败。"));
    setAttempt((value) => value + 1);
  }

  async function readMessages(accountId: string) {
    try { setMessages(await fetchMailboxMessages(accountId)); setMessage("已按你的操作读取指定文件夹；仅保存邮件摘要。"); }
    catch { setError("邮件读取失败，请先测试连接并检查文件夹。"); }
  }

  async function associateMessage(message: MailMessage) {
    const values = association[message.message_id] ?? { opportunity_id: "", application_id: "" };
    try {
      const saved = await associateMailboxMessage(message.message_id, values);
      setMessages((current) => current.map((item) => item.message_id === saved.message_id ? saved : item));
      setMessage("邮件关联已保存，可在岗位和 Application 中继续查看。");
    } catch { setError("邮件关联未保存，请检查 ID。"); }
  }

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
        <Section title="邮箱连接" icon={ShieldCheck} description="密码只保存到系统凭据管理器；连接测试和读取都必须由你主动点击。">
          <div className="analysis-form">
            <div className="form-grid"><Field label="邮箱地址"><input className="input" value={accountForm.username} onChange={(event) => setAccountForm({ ...accountForm, username: event.target.value })} /></Field><Field label="IMAP 主机"><input className="input" value={accountForm.imap_host} onChange={(event) => setAccountForm({ ...accountForm, imap_host: event.target.value })} /></Field><Field label="应用专用密码"><input className="input" type="password" value={accountForm.secret} onChange={(event) => setAccountForm({ ...accountForm, secret: event.target.value })} /></Field></div>
            <div className="button-row"><Button variant="secondary" onClick={() => void saveAccount()}>保存安全配置</Button>{accounts[0] && <><Button variant="secondary" onClick={() => void testAccount(accounts[0].account_id)}>测试连接</Button><Button variant="secondary" onClick={() => void readMessages(accounts[0].account_id)}>手动读取 INBOX</Button></>}</div>
          </div>
          {accounts.map((account) => <p className="text-aux" key={account.account_id}>当前账户：{account.username} · {account.last_test_status === "ok" ? "连接正常" : "尚未测试"}</p>)}
          {messages.length > 0 && <div className="record-list">{messages.map((item) => { const values = association[item.message_id] ?? { opportunity_id: item.opportunity_id ?? "", application_id: item.application_id ?? "" }; return <article className="record-list__item" key={item.message_id}><strong>{item.subject || "无主题"}</strong><p className="text-aux">发件人：{item.sender || "未知"} · 文件夹：{item.folder}</p><p>{item.preview}</p><div className="button-row"><input className="input" aria-label={`岗位 ID ${item.message_id}`} placeholder="岗位 ID" value={values.opportunity_id} onChange={(event) => setAssociation({ ...association, [item.message_id]: { ...values, opportunity_id: event.target.value } })} /><input className="input" aria-label={`Application ID ${item.message_id}`} placeholder="Application ID" value={values.application_id} onChange={(event) => setAssociation({ ...association, [item.message_id]: { ...values, application_id: event.target.value } })} /><Button variant="secondary" onClick={() => void associateMessage(item)}>关联</Button></div></article>; })}</div>}
        </Section>
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
