import { Brain, Check, Plus, ShieldCheck, Trash2, X } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  createMemoryProposal, deleteMemory, listMemories, listMemoryProposals,
  reviewMemoryProposal, type MemoryProposal, type MemorySearchResult, type MemoryType,
} from "../api/memory";

const typeLabels: Record<MemoryType, string> = {
  profile: "个人档案", preference: "偏好", fact: "事实候选", task: "任务", interest: "兴趣",
};

export function ContextPage() {
  const [memories, setMemories] = useState<MemorySearchResult[]>([]);
  const [proposals, setProposals] = useState<MemoryProposal[]>([]);
  const [memoryType, setMemoryType] = useState<MemoryType>("preference");
  const [content, setContent] = useState("");
  const [proposalEdits, setProposalEdits] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("正在读取本地记忆…");
  const [pending, setPending] = useState(false);

  const reload = useCallback(async (signal?: AbortSignal) => {
    try {
      const [confirmed, candidates] = await Promise.all([
        listMemories(signal), listMemoryProposals(signal),
      ]);
      setMemories(confirmed);
      setProposals(candidates);
      setMessage("");
    } catch (error) {
      if (!signal?.aborted) setMessage(`记忆暂不可用：${(error as Error).message}`);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void reload(controller.signal);
    return () => controller.abort();
  }, [reload]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (!content.trim()) return;
    setPending(true);
    try {
      await createMemoryProposal(memoryType, content.trim());
      setContent("");
      await reload();
    } catch (error) {
      setMessage(`无法创建候选记忆：${(error as Error).message}`);
    } finally {
      setPending(false);
    }
  }

  async function review(proposal: MemoryProposal, decision: "approved" | "rejected") {
    setPending(true);
    try {
      await reviewMemoryProposal(
        proposal.proposal_id,
        decision,
        decision === "approved" ? proposalEdits[proposal.proposal_id] ?? proposal.content : undefined,
      );
      await reload();
    } catch (error) {
      setMessage(`无法审核候选记忆：${(error as Error).message}`);
    } finally {
      setPending(false);
    }
  }

  async function remove(memoryId: string) {
    setPending(true);
    try {
      await deleteMemory(memoryId);
      await reload();
    } catch (error) {
      setMessage(`无法删除记忆：${(error as Error).message}`);
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="page context-page">
      <div className="page-heading">
        <div><p className="eyebrow">个人上下文</p><h1>我的</h1><p>只保存你确认过的长期信息；候选记忆不会自动成为事实。</p></div>
        <span className="service-status"><ShieldCheck size={16} />用户确认</span>
      </div>
      {message && <p className="knowledge-message">{message}</p>}
      <section className="context-grid">
        <div className="context-panel">
          <div className="section-heading"><h2>已确认记忆</h2><span>{memories.length} 条</span></div>
          {memories.length === 0 ? <p className="context-empty">还没有已确认记忆。</p> : memories.map(({ memory }) => (
            <article className="memory-card" key={memory.memory_id}>
              <div><span>{typeLabels[memory.memory_type]}</span><small>第 {memory.revision} 版</small></div>
              <p>{memory.content}</p>
              <small>来源：{memory.source_locator} · 可信度 {Math.round(memory.confidence * 100)}%</small>
              <button type="button" disabled={pending} onClick={() => void remove(memory.memory_id)}><Trash2 size={14} />删除</button>
            </article>
          ))}
        </div>
        <div className="context-panel">
          <div className="section-heading"><h2>需要你确认</h2><span>{proposals.length} 条</span></div>
          {proposals.length === 0 ? <p className="context-empty">暂无候选记忆。</p> : proposals.map((proposal) => (
            <article className="memory-card memory-proposal" key={proposal.proposal_id}>
              <div><span>{typeLabels[proposal.memory_type]}</span><small>候选</small></div>
              <textarea
                aria-label="编辑候选记忆"
                value={proposalEdits[proposal.proposal_id] ?? proposal.content}
                onChange={(event) => setProposalEdits((current) => ({
                  ...current, [proposal.proposal_id]: event.target.value,
                }))}
              />
              <div className="memory-actions">
                <button type="button" disabled={pending} onClick={() => void review(proposal, "approved")}><Check size={14} />确认</button>
                <button type="button" disabled={pending} onClick={() => void review(proposal, "rejected")}><X size={14} />拒绝</button>
              </div>
            </article>
          ))}
        </div>
      </section>
      <form className="context-capture" onSubmit={submit}>
        <div><Brain size={20} /><div><p className="eyebrow">手动记录</p><h2>添加候选记忆</h2></div></div>
        <select aria-label="记忆类型" value={memoryType} onChange={(event) => setMemoryType(event.target.value as MemoryType)}>
          {Object.entries(typeLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
        </select>
        <textarea aria-label="记忆内容" value={content} onChange={(event) => setContent(event.target.value)} placeholder="例如：我更偏好本地优先、证据充分的 AI 工程岗位" />
        <button type="submit" disabled={pending || !content.trim()}><Plus size={15} />加入待确认</button>
        <small>模型、插件和历史导入也只能写入同一个待确认队列，不能直接修改你的长期记忆。</small>
      </form>
    </main>
  );
}
