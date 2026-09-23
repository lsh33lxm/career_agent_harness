import {
  BarChart3, BookOpenText, BriefcaseBusiness, Code2, MessageSquareText, Search,
  ShieldCheck,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { apiRequest } from "../api/client";
import {
  createWikiOperation,
  createWikiHealthProposal,
  createKnowledgeProposal,
  getWikiHealth,
  getWikiRevisions,
  reviewKnowledgeProposal,
  reviewWikiOperation,
  type KnowledgeProposal,
  type KnowledgeSearchPage,
  type KnowledgeSearchResult,
  type WikiHealthReport,
} from "../api/knowledge";
import {
  getLegacyKnowledgeOverview,
  type LegacyKnowledgeItem,
  type LegacyKnowledgeOverview,
} from "../api/legacy";
import { SourceConnectorsPanel } from "./SourceConnectorsPanel";
import { getDemoStory } from "../api/demoStory";
import type { DemoStory } from "../api/demoStory";

const categoryLabels: Record<string, string> = {
  personal_fact: "个人事实", project_evidence: "项目证据", skill: "技能",
  star_story: "STAR 故事", interview_story: "面试故事", preference: "偏好",
  target_role: "目标岗位", company: "公司", market_signal: "市场信号",
  template: "模板", application_history: "申请历史",
};
const statusLabels: Record<string, string> = {
  draft: "草稿", proposed: "待确认", approved: "已确认", archived: "已归档",
};
const reviewLabels: Record<string, string> = {
  historical_unconfirmed: "历史未确认", needs_review: "待复核", duplicate: "重复待复核",
};

const editableCategories = Object.entries(categoryLabels);

interface WikiEditDraft {
  knowledgeId: string;
  baseRevision: number;
  category: string;
  title: string;
  content: string;
  evidenceRefs: string[];
}

function shortHash(value: string): string {
  return `${value.slice(0, 8)}…${value.slice(-6)}`;
}

function HistoricalItem({ item }: { item: LegacyKnowledgeItem }) {
  return (
    <article className="knowledge-history-item">
      <div>
        <span>{reviewLabels[item.review_status] ?? "历史来源"}</span>
        {item.topic && <span>{item.topic}</span>}
      </div>
      <h3>{item.title}</h3>
      <p>{[item.company, item.role, item.observed_at].filter(Boolean).join(" · ") || "来源未提供上下文"}</p>
      <small title={item.source_sha256}>
        {item.source_path} · 第 {item.row_number} 行 · SHA-256 {shortHash(item.source_sha256)}
      </small>
    </article>
  );
}

export function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<KnowledgeSearchPage | null>(null);
  const [message, setMessage] = useState("输入关键词检索已确认知识与精确来源。");
  const [overview, setOverview] = useState<LegacyKnowledgeOverview | null>(null);
  const [overviewMessage, setOverviewMessage] = useState("正在读取历史知识投影…");
  const [wikiHealth, setWikiHealth] = useState<WikiHealthReport | null>(null);
  const [healthProposal, setHealthProposal] = useState<KnowledgeProposal | null>(null);
  const [wikiDraft, setWikiDraft] = useState<WikiEditDraft | null>(null);
  const [wikiProposal, setWikiProposal] = useState<KnowledgeProposal | null>(null);
  const [wikiBusy, setWikiBusy] = useState(false);
  const [operationTarget, setOperationTarget] = useState<string | null>(null);
  const [operationTitle, setOperationTitle] = useState("");
  const [operationSlug, setOperationSlug] = useState("");
  const [operationProposal, setOperationProposal] = useState<{
    operation_id: string;
    operation: "rename" | "archive" | "move";
  } | null>(null);
  const [demoStory, setDemoStory] = useState<DemoStory | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    getLegacyKnowledgeOverview(controller.signal)
      .then((value) => {
        setOverview(value);
        setOverviewMessage("");
      })
      .catch((error: Error) => {
        if (!controller.signal.aborted) setOverviewMessage(`历史知识暂不可用：${error.message}`);
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getDemoStory(controller.signal).then((value) => {
      if (!controller.signal.aborted) setDemoStory(value);
    }).catch(() => {
      if (!controller.signal.aborted) setDemoStory(null);
    });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    getWikiHealth(controller.signal).then(setWikiHealth).catch(() => setWikiHealth(null));
    return () => controller.abort();
  }, []);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage("正在检索…");
    try {
      const data = await apiRequest<KnowledgeSearchPage>("/api/v1/knowledge/search", {
        method: "POST",
        body: JSON.stringify({ query, limit: 20 }),
      });
      setResult(data);
      setMessage(data.message ?? (data.items.length ? "" : "没有可引用的已确认知识。"));
    } catch (error) {
      setMessage("知识库暂不可用：" + (error as Error).message);
    }
  }

  async function startWikiEdit(item: KnowledgeSearchResult) {
    setWikiBusy(true);
    setMessage("正在读取页面当前版本…");
    try {
      const revisions = await getWikiRevisions(item.knowledge_id);
      const current = revisions.find((revision) => revision.revision === item.revision);
      if (!current) throw new Error("找不到当前页面版本");
      setWikiDraft({
        knowledgeId: item.knowledge_id,
        baseRevision: item.revision,
        category: item.category,
        title: current.title,
        content: current.content,
        evidenceRefs: item.citation.evidence_refs,
      });
      setWikiProposal(null);
      setMessage("编辑内容会先形成待确认修订，不会直接覆盖当前页面。");
    } catch (error) {
      setMessage(`页面读取失败：${(error as Error).message}`);
    } finally {
      setWikiBusy(false);
    }
  }

  async function proposeWikiEdit(event: FormEvent) {
    event.preventDefault();
    if (!wikiDraft) return;
    setWikiBusy(true);
    try {
      setWikiProposal(await createKnowledgeProposal({
        category: wikiDraft.category,
        title: wikiDraft.title,
        content: wikiDraft.content,
        evidence_refs: wikiDraft.evidenceRefs,
        target_knowledge_id: wikiDraft.knowledgeId,
        base_revision: wikiDraft.baseRevision,
      }));
      setMessage("修订提案已保存，等待你批准或拒绝。");
    } catch (error) {
      setMessage(`修订提案保存失败：${(error as Error).message}`);
    } finally {
      setWikiBusy(false);
    }
  }

  async function reviewWikiEdit(decision: "approved" | "rejected") {
    if (!wikiProposal) return;
    setWikiBusy(true);
    try {
      await reviewKnowledgeProposal(
        wikiProposal.proposal_id,
        decision,
        decision === "approved" ? "用户确认桌面端 Wiki 修订" : "用户拒绝桌面端 Wiki 修订",
      );
      setWikiDraft(null);
      setWikiProposal(null);
      setMessage(decision === "approved" ? "修订已批准并发布为新版本。" : "修订已拒绝，当前页面未改变。");
    } catch (error) {
      setMessage(`修订审核失败：${(error as Error).message}`);
    } finally {
      setWikiBusy(false);
    }
  }

  async function proposePageOperation(operation: "rename" | "archive") {
    if (!operationTarget) return;
    setWikiBusy(true);
    try {
      const proposal = await createWikiOperation(operationTarget, {
        operation,
        requested_by: "用户",
        ...(operation === "rename" ? { new_title: operationTitle, new_slug: operationSlug } : {}),
      });
      setOperationProposal({ operation_id: proposal.operation_id, operation: proposal.operation });
      setMessage("页面治理提案已保存，等待你批准或拒绝。");
    } catch (error) {
      setMessage(`页面治理提案保存失败：${(error as Error).message}`);
    } finally {
      setWikiBusy(false);
    }
  }

  async function proposeHealthFixes() {
    setWikiBusy(true);
    try {
      const proposal = await createWikiHealthProposal();
      setHealthProposal(proposal);
      setMessage("Wiki 健康修复建议已保存，等待你审核；不会自动改动页面。");
    } catch (error) {
      setMessage(`健康修复建议生成失败：${(error as Error).message}`);
    } finally {
      setWikiBusy(false);
    }
  }

  async function reviewPageOperation(decision: "approved" | "rejected") {
    if (!operationProposal) return;
    setWikiBusy(true);
    try {
      await reviewWikiOperation(operationProposal.operation_id, decision, "用户确认页面治理操作");
      setOperationTarget(null);
      setOperationProposal(null);
      setMessage(decision === "approved" ? "页面治理操作已批准。" : "页面治理操作已拒绝，页面未改变。");
    } catch (error) {
      setMessage(`页面治理审核失败：${(error as Error).message}`);
    } finally {
      setWikiBusy(false);
    }
  }

  return (
    <main className="page knowledge-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">职业知识</p>
          <h1>知识</h1>
          <p>把历史岗位、技能需求与面试记录放在同一个可追溯视图中。</p>
        </div>
        <span className="service-status"><ShieldCheck size={16} />证据约束</span>
      </div>

      {overviewMessage && <p className="knowledge-message">{overviewMessage}</p>}
      {demoStory?.available && <section className="knowledge-demo-story" aria-label="演示闭环关联">
        <div><p className="eyebrow">演示闭环</p><h2>岗位、证据、简历与申请关联</h2><p>这些关联来自本地 Demo 数据库，可从历史事件回溯，不代表真实投递。<Link to="/opportunities">返回岗位</Link> · <Link to="/history">查看历史</Link> · <Link to="/resume">查看简历</Link></p></div>
        <div className="knowledge-story-links">{(demoStory.resume_patches ?? []).map((patch) => <span key={patch.patch_id}><strong>Resume Patch</strong>{patch.review_source}<small>{patch.patch_id}#{patch.revision} · {patch.reviewed_at ?? "尚未建立关联"} · {patch.operations.flatMap((item) => item.evidence_ids).join("、") || "尚未建立关联"}</small></span>)}</div>
        <div className="knowledge-story-links">{demoStory.links.map((link) => <span key={`${link.kind}-${link.id}`}><strong>{link.kind}</strong>{link.label}<small>{link.id}</small></span>)}</div>
      </section>}
      {overview && overview.job_count === 0 && (
        <section className="knowledge-empty">
          <BookOpenText size={24} />
          <div><h2>还没有历史知识数据</h2><p>前往“机会”导入只读 Agent Radar 数据后，这里会显示岗位趋势、技能和面试题。</p></div>
          <a href="/opportunities">前往机会</a>
        </section>
      )}
      {overview && overview.job_count > 0 && (
        <>
          <section className="knowledge-metrics" aria-label="历史知识概况">
            <div><BriefcaseBusiness size={18} /><strong>{overview.job_count.toLocaleString("zh-CN")}</strong><span>岗位记录</span></div>
            <div><MessageSquareText size={18} /><strong>{overview.interview_count.toLocaleString("zh-CN")}</strong><span>面试记录</span></div>
            <div><BookOpenText size={18} /><strong>{overview.question_count.toLocaleString("zh-CN")}</strong><span>问题记录</span></div>
            <div><Code2 size={18} /><strong>{overview.coding_count.toLocaleString("zh-CN")}</strong><span>刷题记录</span></div>
          </section>
          <section className="knowledge-overview-grid">
            <article className="knowledge-panel knowledge-skills">
              <div className="knowledge-panel-heading"><div><p className="eyebrow">岗位需求</p><h2>技能关键词</h2></div><BarChart3 size={20} /></div>
              <div className="knowledge-chip-list">
                {overview.top_skills.map((item) => <span key={item.label}>{item.label}<strong>{item.count}</strong></span>)}
              </div>
            </article>
            <article className="knowledge-panel">
              <div className="knowledge-panel-heading"><div><p className="eyebrow">样本分布</p><h2>岗位趋势</h2></div><BriefcaseBusiness size={20} /></div>
              <div className="knowledge-trend-columns">
                <div><h3>公司</h3>{overview.top_companies.map((item) => <p key={item.label}><span>{item.label}</span><strong>{item.count}</strong></p>)}</div>
                <div><h3>地点</h3>{overview.top_locations.map((item) => <p key={item.label}><span>{item.label}</span><strong>{item.count}</strong></p>)}</div>
              </div>
            </article>
          </section>
          <section className="knowledge-history-grid">
            <div className="knowledge-history-column">
              <div className="knowledge-section-heading"><div><p className="eyebrow">面试准备</p><h2>近期问题</h2></div><span>历史未确认投影</span></div>
              {overview.questions.map((item) => <HistoricalItem item={item} key={item.record_id} />)}
            </div>
            <div className="knowledge-history-column">
              <div className="knowledge-section-heading"><div><p className="eyebrow">经历样本</p><h2>面试记录</h2></div><span>历史未确认投影</span></div>
              {overview.interviews.map((item) => <HistoricalItem item={item} key={item.record_id} />)}
            </div>
          </section>
          <p className="knowledge-authority-note">
            以上内容来自 Legacy 只读投影，共 {overview.needs_review_count} 条需要复核；统计不等于个人事实，也不会自动进入简历或能力状态。
          </p>
        </>
      )}

      {wikiHealth && (
        <section className="knowledge-wiki-health" aria-label="Wiki 健康状态">
          <div><p className="eyebrow">知识治理</p><h2>Wiki 健康度 {wikiHealth.score}</h2></div>
          <p>{wikiHealth.page_count} 个页面 · {wikiHealth.link_count} 条链接 · {wikiHealth.issues.length} 个待处理问题</p>
          <small>仅检查孤立页面、重复标题、过期链接、缺少引用和提示注入；不会自动发布或修复。</small>
          <div className="plugin-actions"><button type="button" disabled={wikiBusy} onClick={() => void proposeHealthFixes()}>生成修复建议</button>{healthProposal && <span role="status">已生成待审核建议：{healthProposal.proposal_id}</span>}</div>
        </section>
      )}

      <SourceConnectorsPanel />

      <section className="knowledge-canonical-search">
        <div><p className="eyebrow">已确认知识</p><h2>精确检索</h2></div>
        <form className="knowledge-search" onSubmit={submit}>
          <Search size={17} aria-hidden="true" />
          <label className="sr-only" htmlFor="knowledge-query">检索知识</label>
          <input id="knowledge-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索项目、技能、面经或岗位资料" />
          <button type="submit">检索</button>
        </form>
        {message && <p className="knowledge-message">{message}</p>}
      </section>
      {result && (
        <section className="knowledge-results" aria-label="知识检索结果">
          {result.items.map((item) => (
            <article className="knowledge-result" key={item.knowledge_id + "-" + item.revision}>
              <div className="knowledge-result-heading">
                <h2>{item.title}</h2>
                <span>{categoryLabels[item.category] ?? item.category} · {statusLabels[item.status] ?? item.status}</span>
              </div>
              <p>{item.snippet}</p>
              <small>引用 {item.knowledge_id}#{item.revision} · {item.citation.evidence_refs.join("、") || "无证据引用"}</small>
              <div className="plugin-actions">
                <button type="button" disabled={wikiBusy} onClick={() => void startWikiEdit(item)}>提出修订</button>
                <button type="button" disabled={wikiBusy} onClick={() => { setOperationTarget(item.knowledge_id); setOperationTitle(item.title); setOperationSlug(""); setOperationProposal(null); }}>页面治理</button>
              </div>
              {operationTarget === item.knowledge_id && (
                <div className="wiki-edit-form" aria-label="页面治理">
                  <p>移动、重命名和归档都必须先形成提案，再由你批准。</p>
                  {!operationProposal ? (
                    <>
                      <label>新标题<input value={operationTitle} maxLength={512} onChange={(event) => setOperationTitle(event.target.value)} /></label>
                      <label>新 slug（可选）<input value={operationSlug} maxLength={255} onChange={(event) => setOperationSlug(event.target.value)} placeholder="例如 platform-engineering" /></label>
                      <div className="plugin-actions"><button type="button" disabled={wikiBusy || !operationTitle.trim()} onClick={() => void proposePageOperation("rename")}>提出重命名</button><button type="button" disabled={wikiBusy} onClick={() => void proposePageOperation("archive")}>提出归档</button><button type="button" onClick={() => setOperationTarget(null)}>取消</button></div>
                    </>
                  ) : (
                    <div className="wiki-review-actions" role="region" aria-label="页面治理审核">
                      <p>治理提案已保存。批准后才会应用到 Wiki 页面。</p>
                      <div className="plugin-actions"><button type="button" disabled={wikiBusy} onClick={() => void reviewPageOperation("approved")}>批准操作</button><button type="button" disabled={wikiBusy} onClick={() => void reviewPageOperation("rejected")}>拒绝操作</button></div>
                    </div>
                  )}
                </div>
              )}
              {wikiDraft?.knowledgeId === item.knowledge_id && (
                <form className="wiki-edit-form" onSubmit={proposeWikiEdit}>
                  <p>当前版本 #{wikiDraft.baseRevision}。标题、分类和正文修改只会创建提案。</p>
                  <label>页面标题<input value={wikiDraft.title} maxLength={512} required onChange={(event) => setWikiDraft({ ...wikiDraft, title: event.target.value })} /></label>
                  <label>页面分类<select value={wikiDraft.category} onChange={(event) => setWikiDraft({ ...wikiDraft, category: event.target.value })}>{editableCategories.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
                  <label>页面正文<textarea value={wikiDraft.content} required rows={10} onChange={(event) => setWikiDraft({ ...wikiDraft, content: event.target.value })} /></label>
                  {!wikiProposal ? (
                    <div className="plugin-actions"><button type="submit" disabled={wikiBusy}>保存为待确认修订</button><button type="button" onClick={() => setWikiDraft(null)}>取消</button></div>
                  ) : (
                    <div className="wiki-review-actions" role="region" aria-label="修订审核">
                      <p>提案已保存。批准后才会生成新版本；拒绝不会改动当前页面。</p>
                      <div className="plugin-actions"><button type="button" disabled={wikiBusy} onClick={() => void reviewWikiEdit("approved")}>批准并发布</button><button type="button" disabled={wikiBusy} onClick={() => void reviewWikiEdit("rejected")}>拒绝修订</button></div>
                    </div>
                  )}
                </form>
              )}
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
