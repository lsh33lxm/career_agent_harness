import {
  BarChart3, BookOpenText, BriefcaseBusiness, Building2, Code2, FileText, FolderKanban,
  Heart, History, MessageSquareText, MessagesSquare, Search, ShieldCheck, Sparkles,
  Star, Target, TrendingUp, UserRound, Wrench,
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
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState } from "../components/ui/States";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { ErrorNotice, InlineNotice } from "../components/ui/Notice";

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

const categoryIcons: Record<string, typeof FileText> = {
  personal_fact: UserRound, project_evidence: FolderKanban, skill: Wrench,
  star_story: Star, interview_story: MessagesSquare, preference: Heart,
  target_role: Target, company: Building2, market_signal: TrendingUp,
  template: FileText, application_history: History,
};

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
        <span className="badge">{reviewLabels[item.review_status] ?? "历史来源"}</span>
        {item.topic && <span className="badge badge--green">{item.topic}</span>}
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
  const [searchDetail, setSearchDetail] = useState("");
  const [overview, setOverview] = useState<LegacyKnowledgeOverview | null>(null);
  const [overviewMessage, setOverviewMessage] = useState("正在读取历史知识投影…");
  const [overviewDetail, setOverviewDetail] = useState("");
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
        if (!controller.signal.aborted) {
          setOverviewMessage("历史知识暂不可用，请确认本地服务已启动。");
          setOverviewDetail(error.message);
        }
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
      setSearchDetail("");
      setMessage(data.message ?? (data.items.length ? "" : "没有可引用的已确认知识。"));
    } catch (error) {
      setMessage("知识库暂不可用，请确认本地服务已启动。");
      setSearchDetail((error as Error).message);
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
      setSearchDetail("");
    } catch (error) {
      setMessage("页面读取失败，请重试。");
      setSearchDetail((error as Error).message);
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
      setSearchDetail("");
    } catch (error) {
      setMessage("修订提案保存失败，请重试。");
      setSearchDetail((error as Error).message);
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
      setSearchDetail("");
    } catch (error) {
      setMessage("修订审核失败，请重试。");
      setSearchDetail((error as Error).message);
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
      setSearchDetail("");
    } catch (error) {
      setMessage("页面治理提案保存失败，请重试。");
      setSearchDetail((error as Error).message);
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
      setSearchDetail("");
    } catch (error) {
      setMessage("健康修复建议生成失败，请重试。");
      setSearchDetail((error as Error).message);
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
      setSearchDetail("");
    } catch (error) {
      setMessage("页面治理审核失败，请重试。");
      setSearchDetail((error as Error).message);
    } finally {
      setWikiBusy(false);
    }
  }

  return (
    <main className="page page--wide">
      <PageHeader
        eyebrow="职业知识"
        title="知识"
        description="把历史岗位、技能需求与面试记录放在同一个可追溯视图中。"
        actions={<span className="badge badge--green"><ShieldCheck size={13} aria-hidden="true" />证据约束</span>}
      />

      {overviewMessage && (
        <div style={{ marginBottom: "var(--space-4)" }}>
          {overviewDetail
            ? <ErrorNotice label={overviewMessage} detail={overviewDetail} />
            : <InlineNotice tone="muted" role="status">{overviewMessage}</InlineNotice>}
        </div>
      )}
      {demoStory?.available && (
        <Surface>
          <Section title="演示闭环追溯" description="关联均读取自隔离 Demo Career Core，缺少的关联会明确标记。">
            <p>岗位 {demoStory.opportunity_id ?? "尚未建立关联"} · Evidence {demoStory.evidence_ref_id ?? "尚未建立关联"} · Revision {demoStory.resume_revision_id ?? "尚未建立关联"}</p>
            <div className="knowledge-story-links">
              {(demoStory.resume_patches ?? []).map((patch) => (
                <span key={patch.patch_id}><strong>Resume Patch · {patch.review_status}</strong><small>{patch.patch_id}#{patch.revision} · {patch.review_source} · {patch.reviewed_at ?? "尚未建立关联"} · {patch.operations.flatMap((item) => item.evidence_ids).join("、") || "尚未建立关联"}</small></span>
              ))}
              {demoStory.links.map((link) => <span key={`${link.kind}-${link.id}`}><strong>{link.kind} · {link.label}</strong><small>{link.id}</small></span>)}
            </div>
            <p>Application {demoStory.application_id ?? "尚未建立关联"} · 状态 {demoStory.application_state ?? "尚未建立关联"}</p>
            <div className="resume-actions"><Link className="btn btn--secondary" to="/opportunities">返回岗位</Link><Link className="btn btn--secondary" to="/history">查看历史</Link><Link className="btn btn--secondary" to="/resume">查看简历</Link></div>
          </Section>
        </Surface>
      )}

      <SourceConnectorsPanel />

      <Surface>
        <Section title="精确检索" description="已确认知识" meta={`检索范围：已确认知识与精确来源`}>
          <form className="knowledge-search" onSubmit={(event) => void submit(event)}>
            <Search size={16} aria-hidden="true" />
            <label className="sr-only" htmlFor="knowledge-query">检索知识</label>
            <input id="knowledge-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="搜索项目、技能、面经或岗位资料" />
            <Button variant="primary" type="submit">检索</Button>
          </form>
          {message && (
            <div style={{ marginTop: "var(--space-3)" }}>
              {searchDetail
                ? <ErrorNotice label={message} detail={searchDetail} />
                : <InlineNotice tone={message.includes("失败") ? "danger" : "muted"} role={message.includes("失败") ? "alert" : "status"}>{message}</InlineNotice>}
            </div>
          )}
        </Section>
      </Surface>

      {overview && overview.job_count === 0 && (
        <Surface>
          <Section title="历史知识" ariaLabel="历史知识">
            <EmptyState
              icon={BookOpenText}
              title="还没有历史知识数据"
              description="前往“机会”导入只读 Agent Radar 数据后，这里会显示岗位趋势、技能和面试题。"
              action={<a className="btn btn--primary" href="/opportunities">前往机会</a>}
            />
          </Section>
        </Surface>
      )}

      {overview && overview.job_count > 0 && (
        <Surface>
          <div className="metrics-strip" aria-label="历史知识概况">
            <div><span><BriefcaseBusiness size={13} aria-hidden="true" /> 岗位记录</span><strong>{overview.job_count.toLocaleString("zh-CN")}</strong></div>
            <div><span><MessageSquareText size={13} aria-hidden="true" /> 面试记录</span><strong>{overview.interview_count.toLocaleString("zh-CN")}</strong></div>
            <div><span><BookOpenText size={13} aria-hidden="true" /> 问题记录</span><strong>{overview.question_count.toLocaleString("zh-CN")}</strong></div>
            <div><span><Code2 size={13} aria-hidden="true" /> 刷题记录</span><strong>{overview.coding_count.toLocaleString("zh-CN")}</strong></div>
          </div>
          <div className="knowledge-grid-2">
            <Section title="技能关键词" description="岗位需求" meta={<BarChart3 size={15} aria-hidden="true" />}>
              <div className="knowledge-chip-list">
                {overview.top_skills.map((item) => <span key={item.label}>{item.label}<strong>{item.count}</strong></span>)}
              </div>
            </Section>
            <Section title="岗位趋势" description="样本分布" meta={<BriefcaseBusiness size={15} aria-hidden="true" />}>
              <div className="knowledge-trend-columns">
                <div><h3>公司</h3>{overview.top_companies.map((item) => <p key={item.label}><span>{item.label}</span><strong>{item.count}</strong></p>)}</div>
                <div><h3>地点</h3>{overview.top_locations.map((item) => <p key={item.label}><span>{item.label}</span><strong>{item.count}</strong></p>)}</div>
              </div>
            </Section>
            <Section title="近期问题" description="面试准备" meta="历史未确认投影">
              {overview.questions.map((item) => <HistoricalItem item={item} key={item.record_id} />)}
            </Section>
            <Section title="面试记录" description="经历样本" meta="历史未确认投影">
              {overview.interviews.map((item) => <HistoricalItem item={item} key={item.record_id} />)}
            </Section>
          </div>
          <div className="section">
            <InlineNotice tone="muted">
              以上内容来自 Legacy 只读投影，共 {overview.needs_review_count} 条需要复核；统计不等于个人事实，也不会自动进入简历或能力状态。
            </InlineNotice>
          </div>
        </Surface>
      )}

      {wikiHealth && (
        <Surface>
          <Section
            title={`Wiki 健康度 ${wikiHealth.score}`}
            description={`${wikiHealth.page_count} 个页面 · ${wikiHealth.link_count} 条链接 · ${wikiHealth.issues.length} 个待处理问题`}
            meta="知识治理"
          >
            <p className="text-aux" style={{ marginBottom: "var(--space-3)" }}>仅检查孤立页面、重复标题、过期链接、缺少引用和提示注入；不会自动发布或修复。</p>
            <div className="resume-actions">
              <Button variant="secondary" loading={wikiBusy} onClick={() => void proposeHealthFixes()}>生成修复建议</Button>
              {healthProposal && <InlineNotice tone="success" role="status">已生成待审核建议：{healthProposal.proposal_id}</InlineNotice>}
            </div>
          </Section>
        </Surface>
      )}

      {result && (
        <div className="knowledge-results" aria-label="知识检索结果">
          {result.items.map((item) => (
            <article className="knowledge-result" key={item.knowledge_id + "-" + item.revision}>
              <div className="knowledge-result__head">
                <span className="section__icon" aria-hidden="true">{(() => { const CategoryIcon = categoryIcons[item.category] ?? FileText; return <CategoryIcon size={15} />; })()}</span>
                <h2>{item.title}</h2>
                <span className="badge">{categoryLabels[item.category] ?? item.category} · {statusLabels[item.status] ?? item.status}</span>
              </div>
              <p>{item.snippet}</p>
              <small className="text-aux">引用 {item.knowledge_id}#{item.revision} · {item.citation.evidence_refs.join("、") || "无证据引用"}</small>
              <div className="resume-actions">
                <Button size="sm" variant="secondary" loading={wikiBusy} onClick={() => void startWikiEdit(item)}>提出修订</Button>
                <Button size="sm" variant="quiet" loading={wikiBusy} onClick={() => { setOperationTarget(item.knowledge_id); setOperationTitle(item.title); setOperationSlug(""); setOperationProposal(null); }}>页面治理</Button>
              </div>
              {operationTarget === item.knowledge_id && (
                <div className="knowledge-edit" aria-label="页面治理">
                  <p className="text-aux">移动、重命名和归档都必须先形成提案，再由你批准。</p>
                  {!operationProposal ? (
                    <>
                      <div className="knowledge-grid-2">
                        <Field label="新标题">
                          <input className="input" value={operationTitle} maxLength={512} onChange={(event) => setOperationTitle(event.target.value)} />
                        </Field>
                        <Field label="新 slug（可选）">
                          <input className="input" value={operationSlug} maxLength={255} onChange={(event) => setOperationSlug(event.target.value)} placeholder="例如 platform-engineering" />
                        </Field>
                      </div>
                      <div className="resume-actions">
                        <Button size="sm" variant="primary" loading={wikiBusy} disabled={!operationTitle.trim()} onClick={() => void proposePageOperation("rename")}>提出重命名</Button>
                        <Button size="sm" variant="secondary" loading={wikiBusy} onClick={() => void proposePageOperation("archive")}>提出归档</Button>
                        <Button size="sm" variant="quiet" onClick={() => setOperationTarget(null)}>取消</Button>
                      </div>
                    </>
                  ) : (
                    <div className="banner banner--info" role="region" aria-label="页面治理审核">
                      <div className="banner__body">
                        <p>治理提案已保存。批准后才会应用到 Wiki 页面。</p>
                        <div className="banner__actions" style={{ marginTop: "var(--space-2)" }}>
                          <Button size="sm" variant="primary" loading={wikiBusy} onClick={() => void reviewPageOperation("approved")}>批准操作</Button>
                          <Button size="sm" variant="secondary" loading={wikiBusy} onClick={() => void reviewPageOperation("rejected")}>拒绝操作</Button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
              {wikiDraft?.knowledgeId === item.knowledge_id && (
                <form className="knowledge-edit" onSubmit={(event) => void proposeWikiEdit(event)}>
                  <p className="text-aux">当前版本 #{wikiDraft.baseRevision}。标题、分类和正文修改只会创建提案。</p>
                  <Field label="页面标题">
                    <input className="input" value={wikiDraft.title} maxLength={512} required onChange={(event) => setWikiDraft({ ...wikiDraft, title: event.target.value })} />
                  </Field>
                  <Field label="页面分类">
                    <select className="select" value={wikiDraft.category} onChange={(event) => setWikiDraft({ ...wikiDraft, category: event.target.value })}>
                      {editableCategories.map(([value, label]) => <option value={value} key={value}>{label}</option>)}
                    </select>
                  </Field>
                  <Field label="页面正文">
                    <textarea className="textarea" value={wikiDraft.content} required rows={10} onChange={(event) => setWikiDraft({ ...wikiDraft, content: event.target.value })} />
                  </Field>
                  {!wikiProposal ? (
                    <div className="resume-actions">
                      <Button size="sm" variant="primary" type="submit" loading={wikiBusy}>保存为待确认修订</Button>
                      <Button size="sm" variant="quiet" onClick={() => setWikiDraft(null)}>取消</Button>
                    </div>
                  ) : (
                    <div className="banner banner--info" role="region" aria-label="修订审核">
                      <div className="banner__body">
                        <p>提案已保存。批准后才会生成新版本；拒绝不会改动当前页面。</p>
                        <div className="banner__actions" style={{ marginTop: "var(--space-2)" }}>
                          <Button size="sm" variant="primary" loading={wikiBusy} onClick={() => void reviewWikiEdit("approved")}>批准并发布</Button>
                          <Button size="sm" variant="secondary" loading={wikiBusy} onClick={() => void reviewWikiEdit("rejected")}>拒绝修订</Button>
                        </div>
                      </div>
                    </div>
                  )}
                </form>
              )}
            </article>
          ))}
        </div>
      )}
    </main>
  );
}
