import { Search, ShieldCheck } from "lucide-react";
import { FormEvent, useState } from "react";

import { apiRequest } from "../api/client";
import type { KnowledgeSearchPage } from "../api/knowledge";

export function KnowledgePage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<KnowledgeSearchPage | null>(null);
  const [message, setMessage] = useState("输入关键词检索本地知识与 exact provenance。");

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage("正在检索…");
    try {
      const data = await apiRequest<KnowledgeSearchPage>("/api/v1/knowledge/search", {
        method: "POST",
        body: JSON.stringify({ query, limit: 20 }),
      });
      setResult(data);
      setMessage(data.message ?? (data.items.length ? "" : "没有可引用的知识。"));
    } catch (error) {
      setMessage("知识库暂不可用：" + (error as Error).message);
    }
  }

  return (
    <main className="page knowledge-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Career Knowledge</p>
          <h1>知识库</h1>
        </div>
        <span className="service-status"><ShieldCheck size={16} />证据约束</span>
      </div>
      <form className="knowledge-search" onSubmit={submit}>
        <Search size={17} aria-hidden="true" />
        <label className="sr-only" htmlFor="knowledge-query">检索知识</label>
        <input
          id="knowledge-query"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="搜索项目、技能、面经或岗位资料"
        />
        <button type="submit">检索</button>
      </form>
      {message && <p className="knowledge-message">{message}</p>}
      {result && (
        <section className="knowledge-results" aria-label="知识检索结果">
          {result.items.map((item) => (
            <article className="knowledge-result" key={item.knowledge_id + "-" + item.revision}>
              <div className="knowledge-result-heading">
                <h2>{item.title}</h2>
                <span>{item.category} · {item.status}</span>
              </div>
              <p>{item.snippet}</p>
              <small>
                引用 {item.knowledge_id}#{item.revision} · {item.citation.evidence_refs.join("、")}
              </small>
            </article>
          ))}
        </section>
      )}
    </main>
  );
}
