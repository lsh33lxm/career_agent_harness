import { Database, FileText, FolderKanban, Github, RefreshCw, Search, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  getProject,
  listProjects,
  type ProjectRead,
} from "../api/projectResume";
import { analyzeGitHubProject, listGitHubAnalyses, saveGitHubToken, type GitHubAnalysis } from "../api/githubProjects";
import { authorityLabels, displayLabel, freshnessLabels, reviewStatusLabels } from "../app/displayLabels";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { InlineNotice } from "../components/ui/Notice";

type ProjectSummary = ProjectRead["project"];

export function ProjectsPage() {
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [detail, setDetail] = useState<ProjectRead | null>(null);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [analyses, setAnalyses] = useState<GitHubAnalysis[]>([]);
  const [repositoryUrl, setRepositoryUrl] = useState("");
  const [privateToken, setPrivateToken] = useState("");
  const [usePrivateToken, setUsePrivateToken] = useState(false);
  const [networkConfirmed, setNetworkConfirmed] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [analysisMessage, setAnalysisMessage] = useState("");

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
    Promise.all([getProject(selectedId, "", controller.signal), listGitHubAnalyses(selectedId, controller.signal)])
      .then(([item, loadedAnalyses]) => { if (!controller.signal.aborted) { setDetail(item); setAnalyses(loadedAnalyses); } })
      .catch(() => {
        if (!controller.signal.aborted) setError("项目详情暂时无法读取，请选择其他项目或重试。");
      });
    return () => controller.abort();
  }, [selectedId, attempt]);

  async function analyze() {
    if (!repositoryUrl.trim() || !networkConfirmed) return;
    setAnalyzing(true); setAnalysisMessage("");
    try {
      if (usePrivateToken && privateToken.trim()) {
        await saveGitHubToken(privateToken.trim());
        setPrivateToken("");
      }
      const result = await analyzeGitHubProject(repositoryUrl.trim(), usePrivateToken);
      setAnalysisMessage("只读分析完成，项目档案已保存。分析结论是项目证据，不会自动成为个人事实。");
      setSelectedId(result.project_id);
      setAttempt((value) => value + 1);
    } catch (reason) {
      setAnalysisMessage(`分析失败：${(reason as Error).message}`);
    } finally { setAnalyzing(false); }
  }

  const filtered = useMemo(() => {
    const normalized = query.trim().toLocaleLowerCase("zh-CN");
    return normalized
      ? projects.filter((item) => item.display_name.toLocaleLowerCase("zh-CN").includes(normalized))
      : projects;
  }, [projects, query]);

  return (
    <main className="page page--wide">
      <PageHeader
        eyebrow="项目档案"
        title="项目与证据"
        description="浏览已登记项目及其来源证据；项目存在不等于个人掌握。"
        art
      />

      <Surface>
        <Section
          title="分析 GitHub 项目"
          icon={Github}
          description="仓库只读拉取到本机受控缓存；不运行代码、Git hooks 或 install script，也不会向 GitHub 写入。"
        >
          <div className="analysis-inline">
            <Field label="公开或私有仓库地址">
              <input
                className="input"
                type="url"
                aria-label="公开或私有仓库地址"
                value={repositoryUrl}
                onChange={(event) => setRepositoryUrl(event.target.value)}
                placeholder="https://github.com/owner/repository"
              />
            </Field>
            <Button
              variant="primary"
              loading={analyzing}
              disabled={!networkConfirmed || !repositoryUrl.trim()}
              onClick={() => void analyze()}
              icon={<Search size={14} aria-hidden="true" />}
            >
              {analyzing ? "正在分析…" : "开始只读分析"}
            </Button>
          </div>
          <div className="analysis-meta">
            <label className="checkbox">
              <input type="checkbox" checked={networkConfirmed} onChange={(event) => setNetworkConfirmed(event.target.checked)} />
              我确认执行一次只读 GitHub 网络请求
            </label>
            <details className="disclosure analysis-token">
              <summary>私有仓库令牌</summary>
              <div className="disclosure__body analysis-form">
                <label className="checkbox">
                  <input type="checkbox" checked={usePrivateToken} onChange={(event) => setUsePrivateToken(event.target.checked)} />
                  使用已保存或新输入的只读令牌
                </label>
                {usePrivateToken && (
                  <Field label="GitHub 只读令牌">
                    <input
                      className="input"
                      type="password"
                      autoComplete="new-password"
                      value={privateToken}
                      onChange={(event) => setPrivateToken(event.target.value)}
                      placeholder="仅保存到 Windows 凭据管理器"
                    />
                  </Field>
                )}
              </div>
            </details>
          </div>
          {analysisMessage && (
            <InlineNotice tone={analysisMessage.startsWith("分析失败") ? "danger" : "success"} role="status">{analysisMessage}</InlineNotice>
          )}
          <div className="analysis-features">
            <span><ShieldCheck size={14} aria-hidden="true" /><strong>只读分析</strong><small>仅抓取公开信息，不执行代码</small></span>
            <span><Database size={14} aria-hidden="true" /><strong>提取来源证据</strong><small>如 README、提交记录、发布信息等</small></span>
            <span><FileText size={14} aria-hidden="true" /><strong>生成项目档案</strong><small>提取技术栈、职责亮点与可验证证据</small></span>
          </div>
        </Section>
      </Surface>

      <Surface ariaLabel="项目浏览器">
        <Section title="项目档案" icon={FolderKanban} meta={loading ? undefined : `${projects.length} 项`}>
          <div className="control-group control-group--2">
            <Field label="搜索项目">
              <input
                className="input"
                aria-label="搜索项目"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="输入项目名称"
              />
            </Field>
            <Button variant="secondary" onClick={() => setAttempt((value) => value + 1)} icon={<RefreshCw size={14} aria-hidden="true" />}>刷新</Button>
          </div>
        </Section>

        <div className="section" style={{ paddingTop: 0 }}>
          {error && <ErrorState compact title="暂时无法读取项目" detail={error} onRetry={() => setAttempt((value) => value + 1)} />}
          {loading && <LoadingState label="正在读取项目列表…" />}
          {!loading && projects.length === 0 && !error && (
            <EmptyState
              icon={FolderKanban}
              title="还没有项目档案"
              description="完成一次项目登记或 GitHub 项目分析后，项目会显示在这里。"
            />
          )}
          {!loading && projects.length > 0 && (
            <div className="record-browser">
              <div className="record-browser__list" aria-label={`项目列表，共 ${filtered.length} 项`}>
                {filtered.map((item) => (
                  <button
                    className={selectedId === item.project_id ? "is-selected" : ""}
                    type="button"
                    key={item.project_id}
                    onClick={() => setSelectedId(item.project_id)}
                  >
                    <span className="project-avatar" aria-hidden="true"><FolderKanban size={15} /></span>
                    <span className="record-browser__item-text">
                      <strong>{item.display_name}</strong>
                      <span>第 {item.revision} 版</span>
                    </span>
                  </button>
                ))}
                {filtered.length === 0 && <p className="text-aux" style={{ padding: "var(--space-4)" }}>没有匹配的项目。</p>}
              </div>
              <div className="record-browser__detail">
                {!detail && <p className="text-aux">请选择一个项目查看详情。</p>}
                {detail && <>
                  <h2>{detail.project.display_name}</h2>
                  <p className="text-aux">当前修订：第 {detail.project.revision} 版 · 记录时间：{detail.project.created_at}</p>
                  <h3>项目证据</h3>
                  <p className="text-aux">以下为每条证据的最新修订，不代表项目历史修订当时的快照。</p>
                  {detail.evidence.length === 0 && <p className="text-aux">此项目尚无已记录证据。</p>}
                  {detail.evidence.map((item) => (
                    <article className="evidence-card" key={item.evidence_id}>
                      <h4>{item.summary}</h4>
                      <p>来源权威：{displayLabel(item.authority, authorityLabels)} · 复核：{displayLabel(item.review_status, reviewStatusLabels)} · 时效：{displayLabel(item.freshness, freshnessLabels)}</p>
                      <details className="disclosure" style={{ marginTop: "var(--space-3)" }}>
                        <summary>查看来源文件</summary>
                        <div className="disclosure__body">
                          <ul>
                            {item.source_manifest.entries.map((entry) => (
                              <li key={entry.relative_path}>{entry.relative_path}<br />SHA-256：{entry.sha256}<br />{entry.byte_length} 字节</li>
                            ))}
                          </ul>
                        </div>
                      </details>
                    </article>
                  ))}
                  <h3>GitHub 静态分析</h3>
                  {analyses.length === 0 && <p className="text-aux">此项目没有 GitHub 分析档案。</p>}
                  {analyses.map((analysis) => (
                    <article className="evidence-card" key={analysis.analysis_id}>
                      <h4>{analysis.repository_url}</h4>
                      <p>固定提交：{analysis.commit_sha.slice(0, 12)} · {analysis.file_count} 个文件 · {analysis.byte_count} 字节</p>
                      <p><strong>技术栈：</strong>{analysis.profile.technology_stack.join("、") || "未识别"}</p>
                      <p><strong>依赖清单：</strong>{analysis.profile.dependency_manifests.join("、") || "未发现"}</p>
                      <p><strong>测试：</strong>{analysis.profile.tests.slice(0, 8).join("、") || "未发现"}</p>
                      <p><strong>部署：</strong>{analysis.profile.deployment.slice(0, 8).join("、") || "未发现"}</p>
                      <p><strong>最近活跃：</strong>{analysis.profile.recent_activity[0] ? `${analysis.profile.recent_activity[0].authored_at} · ${analysis.profile.recent_activity[0].title}` : "未读取到提交记录"}</p>
                      <p><strong>可量化线索：</strong>{analysis.profile.outcome_clues.join("；") || "未发现，不能自动补全"}</p>
                      {analysis.profile.risk_notes.length > 0 && <p><strong>风险提示：</strong>{analysis.profile.risk_notes.join("；")}</p>}
                      <details className="disclosure" style={{ marginTop: "var(--space-3)" }}>
                        <summary>查看分析 provenance</summary>
                        <div className="disclosure__body">
                          <p>README SHA-256：{analysis.readme_sha256 ?? "无"}</p>
                          <p>分析器：{analysis.provenance.analyzer}</p>
                          <p>README：{analysis.provenance.readme ?? "未发现"}</p>
                        </div>
                      </details>
                    </article>
                  ))}
                </>}
              </div>
            </div>
          )}
        </div>
      </Surface>
    </main>
  );
}
