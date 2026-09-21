import { FolderKanban, RefreshCw, Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  getProject,
  listProjects,
  type ProjectRead,
} from "../api/projectResume";

type ProjectSummary = ProjectRead["project"];

export function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<ProjectRead | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    listProjects(controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return;
        setProjects(items);
        setSelectedId((current) => current || items[0]?.project_id || "");
        setLoading(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setError("项目列表暂时无法读取，请检查本地服务后重试。");
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    if (!selectedId) {
      setDetail(null);
      return;
    }
    const controller = new AbortController();
    setError("");
    getProject(selectedId, "", controller.signal)
      .then((item) => { if (!controller.signal.aborted) setDetail(item); })
      .catch(() => {
        if (!controller.signal.aborted) setError("项目详情暂时无法读取，请选择其他项目或重试。");
      });
    return () => controller.abort();
  }, [selectedId, attempt]);

  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("zh-CN");
    return normalized
      ? projects.filter((item) => item.display_name.toLocaleLowerCase("zh-CN").includes(normalized))
      : projects;
  }, [projects, query]);

  return (
    <main className="page record-page">
      <header className="page-heading">
        <div><p className="eyebrow">项目档案</p><h1>项目与证据</h1><p>浏览已登记项目及其来源证据；项目存在不等于个人掌握。</p></div>
      </header>

      <section className="today-panel record-browser" aria-label="项目浏览器">
        <div className="record-browser__toolbar">
          <label><span>搜索项目</span><span className="record-browser__search"><Search size={15} /><input aria-label="搜索项目" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入项目名称" /></span></label>
          <button type="button" onClick={() => setAttempt((value) => value + 1)}><RefreshCw size={15} />刷新</button>
        </div>
        {error && <p className="inline-error" role="alert">{error}</p>}
        {loading && <p role="status">正在读取项目列表…</p>}
        {!loading && projects.length === 0 && <div className="empty-state"><FolderKanban size={24} /><h2>还没有项目档案</h2><p>完成一次项目登记或 GitHub 项目分析后，项目会显示在这里。</p></div>}
        {!loading && projects.length > 0 && (
          <div className="record-browser__layout">
            <div className="record-browser__list" aria-label={`项目列表，共 ${filtered.length} 项`}>
              {filtered.map((item) => <button className={selectedId === item.project_id ? "is-selected" : ""} type="button" key={item.project_id} onClick={() => setSelectedId(item.project_id)}><strong>{item.display_name}</strong><span>第 {item.revision} 版</span></button>)}
              {filtered.length === 0 && <p>没有匹配的项目。</p>}
            </div>
            <div className="record-browser__detail">
              {!detail && <p>请选择一个项目查看详情。</p>}
              {detail && <>
                <h2>{detail.project.display_name}</h2>
                <p>当前修订：第 {detail.project.revision} 版 · 记录时间：{detail.project.created_at}</p>
                <h3>项目证据</h3>
                <p>以下为每条证据的最新修订，不代表项目历史修订当时的快照。</p>
                {detail.evidence.length === 0 && <p>此项目尚无已记录证据。</p>}
                {detail.evidence.map((item) => <article key={item.evidence_id}><h3>{item.summary}</h3><p>来源权威：{item.authority} · 复核：{item.review_status} · 时效：{item.freshness}</p><details><summary>查看来源文件</summary><ul>{item.source_manifest.entries.map((entry) => <li key={entry.relative_path}>{entry.relative_path}<br />SHA-256：{entry.sha256}<br />{entry.byte_length} 字节</li>)}</ul></details></article>)}
              </>}
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
