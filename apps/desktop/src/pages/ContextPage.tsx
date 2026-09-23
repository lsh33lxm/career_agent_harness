import { Brain, Check, ChevronRight, FileText, Heart, ListTodo, Plus, Search, ShieldCheck, Sparkles, Trash2, UserRound, X, type LucideIcon } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import {
  createMemoryProposal, deleteMemory, listMemories, listMemoryProposals,
  reviewMemoryProposal, type MemoryProposal, type MemorySearchResult, type MemoryType,
} from "../api/memory";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState } from "../components/ui/States";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { ErrorNotice, InlineNotice, StatusBanner } from "../components/ui/Notice";

const typeLabels: Record<MemoryType, string> = {
  profile: "个人档案", preference: "偏好", fact: "事实候选", task: "任务", interest: "兴趣",
};

const typeIcons: Record<MemoryType, LucideIcon> = {
  profile: UserRound, preference: Heart, fact: FileText, task: ListTodo, interest: Sparkles,
};

function typeChip(type: MemoryType) {
  const Icon = typeIcons[type];
  return (
    <span className="badge badge--green">
      <Icon size={12} aria-hidden="true" />
      {typeLabels[type]}
    </span>
  );
}

export function ContextPage() {
  const [memories, setMemories] = useState<MemorySearchResult[]>([]);
  const [proposals, setProposals] = useState<MemoryProposal[]>([]);
  const [memoryType, setMemoryType] = useState<MemoryType>("preference");
  const [content, setContent] = useState("");
  const [proposalEdits, setProposalEdits] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("正在读取本地记忆…");
  const [messageDetail, setMessageDetail] = useState("");
  const [pending, setPending] = useState(false);
  const [tab, setTab] = useState<"confirmed" | "pending">("confirmed");
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("");

  const reload = useCallback(async (signal?: AbortSignal) => {
    try {
      const [confirmed, candidates] = await Promise.all([
        listMemories(signal), listMemoryProposals(signal),
      ]);
      setMemories(confirmed);
      setProposals(candidates);
      setMessage("");
      setMessageDetail("");
    } catch (error) {
      if (!signal?.aborted) {
        setMessage("记忆暂不可用，请确认本地服务已启动。");
        setMessageDetail((error as Error).message);
      }
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
      setMessage("无法创建候选记忆，请重试。");
      setMessageDetail((error as Error).message);
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
      setMessage("无法审核候选记忆，请重试。");
      setMessageDetail((error as Error).message);
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
      setMessage("无法删除记忆，请重试。");
      setMessageDetail((error as Error).message);
    } finally {
      setPending(false);
    }
  }

  const filteredMemories = useMemo(() => {
    const query = search.trim().toLowerCase();
    return memories.filter(({ memory }) =>
      (!typeFilter || memory.memory_type === typeFilter)
      && (!query || memory.content.toLowerCase().includes(query)));
  }, [memories, search, typeFilter]);

  const filteredProposals = useMemo(() => {
    const query = search.trim().toLowerCase();
    return proposals.filter((proposal) =>
      (!typeFilter || proposal.memory_type === typeFilter)
      && (!query || proposal.content.toLowerCase().includes(query)));
  }, [proposals, search, typeFilter]);

  return (
    <main className="page page--wide">
      <PageHeader
        eyebrow="个人上下文"
        title="我的"
        description="只保存你确认过的长期信息；候选记忆不会自动成为事实。"
        actions={<span className="badge badge--green"><ShieldCheck size={13} aria-hidden="true" />用户确认</span>}
      />

      <div style={{ marginBottom: "var(--space-4)" }}>
        <StatusBanner tone="info" title="你的记忆仅对你可见，需要你确认后才会被保存。" />
      </div>

      {message && (
        <div style={{ marginBottom: "var(--space-4)" }}>
          {messageDetail
            ? <ErrorNotice label={message} detail={messageDetail} />
            : <InlineNotice tone="muted" role="status">{message}</InlineNotice>}
        </div>
      )}

      <div className="stat-cards">
        <button type="button" className="stat-card" aria-pressed={tab === "confirmed"} onClick={() => setTab("confirmed")}>
          <span className="stat-card__icon stat-card__icon--green"><Check size={17} aria-hidden="true" /></span>
          <span className="stat-card__text"><small>已确认</small><strong>{memories.length} 条</strong></span>
          <ChevronRight size={16} aria-hidden="true" />
        </button>
        <button type="button" className="stat-card" aria-pressed={tab === "pending"} onClick={() => setTab("pending")}>
          <span className="stat-card__icon stat-card__icon--gold"><ListTodo size={17} aria-hidden="true" /></span>
          <span className="stat-card__text"><small>待确认</small><strong>{proposals.length} 条</strong></span>
          <ChevronRight size={16} aria-hidden="true" />
        </button>
      </div>

      <Surface>
        <div className="tab-bar tab-bar--inset" role="tablist" aria-label="记忆审核分区">
          <button type="button" role="tab" aria-selected={tab === "confirmed"} onClick={() => setTab("confirmed")}>已确认 ({memories.length})</button>
          <button type="button" role="tab" aria-selected={tab === "pending"} onClick={() => setTab("pending")}>待确认 ({proposals.length})</button>
          <span className="topbar__spacer" />
          <span className="provider-search">
            <Search size={14} aria-hidden="true" />
            <input
              aria-label="搜索记忆内容"
              placeholder="搜索记忆内容、关键词…"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </span>
          <select className="select memory-filter" aria-label="按类型筛选" value={typeFilter} onChange={(event) => setTypeFilter(event.target.value)}>
            <option value="">全部类型</option>
            {Object.entries(typeLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
          </select>
        </div>

        {tab === "confirmed" && (
          <Section title="已确认记忆" icon={Check} ariaLabel="已确认记忆" meta={`${filteredMemories.length} 条`}>
            {filteredMemories.length === 0 ? (
              <EmptyState compact icon={Check} title={memories.length === 0 ? "还没有已确认记忆。" : "没有匹配的记忆。"} />
            ) : (
              <div className="memory-list">
                {filteredMemories.map(({ memory }) => (
                  <article className="memory-row" key={memory.memory_id}>
                    <div className="memory-row__head">
                      {typeChip(memory.memory_type)}
                      <small>第 {memory.revision} 版</small>
                    </div>
                    <p>{memory.content}</p>
                    <div className="memory-row__meta">
                      <span>来源：{memory.source_locator}</span>
                      <span>{memory.created_at.slice(0, 10)}</span>
                      <span>可信度 {Math.round(memory.confidence * 100)}%</span>
                      <Button size="sm" variant="destructive" loading={pending} onClick={() => void remove(memory.memory_id)} icon={<Trash2 size={13} aria-hidden="true" />}>删除</Button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </Section>
        )}

        {tab === "pending" && (
          <Section title="需要你确认" icon={ListTodo} ariaLabel="需要你确认" meta={`${filteredProposals.length} 条`}>
            {filteredProposals.length === 0 ? (
              <EmptyState compact icon={ListTodo} title={proposals.length === 0 ? "暂无候选记忆。" : "没有匹配的候选记忆。"} />
            ) : (
              <div className="memory-list">
                {filteredProposals.map((proposal) => (
                  <article className="memory-row" key={proposal.proposal_id}>
                    <div className="memory-row__head">
                      <span className="badge badge--gold">{typeLabels[proposal.memory_type]}</span>
                      <small>候选</small>
                    </div>
                    <textarea
                      className="textarea"
                      aria-label="编辑候选记忆"
                      value={proposalEdits[proposal.proposal_id] ?? proposal.content}
                      onChange={(event) => setProposalEdits((current) => ({
                        ...current, [proposal.proposal_id]: event.target.value,
                      }))}
                    />
                    <div className="memory-actions">
                      <Button size="sm" variant="primary" loading={pending} onClick={() => void review(proposal, "approved")} icon={<Check size={13} aria-hidden="true" />}>确认</Button>
                      <Button size="sm" variant="secondary" loading={pending} onClick={() => void review(proposal, "rejected")} icon={<X size={13} aria-hidden="true" />}>拒绝</Button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </Section>
        )}

        <Section title="添加候选记忆" icon={Brain} description="模型、插件和历史导入也只能写入同一个待确认队列，不能直接修改你的长期记忆。">
          <form className="context-composer" onSubmit={(event) => void submit(event)}>
            <Field label="记忆类型">
              <select
                className="select"
                aria-label="记忆类型"
                value={memoryType}
                onChange={(event) => setMemoryType(event.target.value as MemoryType)}
              >
                {Object.entries(typeLabels).map(([value, label]) => <option value={value} key={value}>{label}</option>)}
              </select>
            </Field>
            <Field label="记忆内容" className="context-composer__content">
              <textarea
                className="textarea"
                aria-label="记忆内容"
                value={content}
                onChange={(event) => setContent(event.target.value)}
                placeholder="例如：我更偏好本地优先、证据充分的 AI 工程岗位"
              />
            </Field>
            <span className="composer-counter" aria-hidden="true">{content.length} 字</span>
            <Button variant="primary" type="submit" loading={pending} disabled={!content.trim()} icon={<Plus size={14} aria-hidden="true" />}>加入待确认</Button>
          </form>
        </Section>
      </Surface>
    </main>
  );
}
