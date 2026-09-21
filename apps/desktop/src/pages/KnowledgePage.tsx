import {
  BarChart3, BookOpenText, BriefcaseBusiness, Code2, MessageSquareText, Search,
  ShieldCheck,
} from "lucide-react";
import { FormEvent, useEffect, useState } from "react";

import { apiRequest } from "../api/client";
import { getWikiHealth, type KnowledgeSearchPage, type WikiHealthReport } from "../api/knowledge";
import {
  getLegacyKnowledgeOverview,
  type LegacyKnowledgeItem,
  type LegacyKnowledgeOverview,
} from "../api/legacy";
import { SourceConnectorsPanel } from "./SourceConnectorsPanel";

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
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
