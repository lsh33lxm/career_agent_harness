import {
  AlertCircle,
  Building2,
  Check,
  Database,
  ExternalLink,
  FileText,
  Inbox,
  MapPin,
  RefreshCw,
  Search,
  Upload,
  X,
} from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { admitStagedJob } from "../api/jobRadar";
import { localizedApiError } from "../api/client";
import { getDemoJob, listDemoJobs } from "../api/demoJobs";
import { approveDemoResume, createDemoResumeRevision, startDemoLoop, type DemoLoopResult } from "../api/demoLoop";
import { getDemoStory, type DemoStory } from "../api/demoStory";
import {
  getLegacyImportStatus,
  getLegacyJob,
  listLegacyJobs,
  runLegacyImport,
  type LegacyImportStatus,
  type LegacyJobDetail,
  type LegacyJobSummary,
} from "../api/legacy";

type LoadState = "loading" | "ready" | "error";

const statusLabels: Record<LegacyJobSummary["status"], string> = {
  staged: "待选择",
  duplicate: "重复待复核",
  admitted: "已加入求职流程",
  rejected: "已忽略",
};

const reviewLabels: Record<LegacyJobSummary["review_status"], string> = {
  historical_unconfirmed: "历史记录 · 未确认",
  needs_review: "内容变化 · 待复核",
  duplicate: "重复记录 · 待复核",
};

const sourceClassLabels: Record<string, string> = {
  unified_job: "统一岗位库",
  cn_jd_event: "国内岗位记录",
  overseas_jd: "海外岗位记录",
  candidate_platform: "候选平台岗位",
  candidate_official: "官方岗位候选",
  candidate_canonical: "Canonical 岗位候选",
  snapshot_overseas: "海外历史快照",
};

function message(error: unknown): string {
  return localizedApiError(error);
}

function shortHash(value: string): string {
  return `${value.slice(0, 10)}…${value.slice(-8)}`;
}

function displayText(value: string | null): string {
  if (!value) return "";
  let parts = [value];
  if (value.trim().startsWith("[") && value.trim().endsWith("]")) {
    try {
      const parsed: unknown = JSON.parse(value);
      if (Array.isArray(parsed)) parts = parsed.map(String);
    } catch {
      parts = [value];
    }
  }
  return parts
    .map((item) => item.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim())
    .filter(Boolean)
    .join("、");
}

function displayTags(values: string[]): string[] {
  const result: string[] = [];
  for (const value of values) {
    const normalized = displayText(value);
    for (const item of normalized.split("、")) {
      const tag = item.trim();
      if (tag && tag.length <= 42 && !result.includes(tag)) result.push(tag);
    }
  }
  return result.slice(0, 5);
}

function displayJd(value: string): string {
  return value
    .split("\n")
    .map((line) => displayText(line))
    .filter(Boolean)
    .join("\n\n");
}

function interviewLabel(value: Record<string, unknown>): string {
  const title = value.title ?? value.round ?? "历史面试记录";
  const date = value.interview_date ?? value.effective_event_date ?? value.published_at;
  return date ? `${String(title)} · ${String(date)}` : String(title);
}

export function JobRadarPanel() {
  const [loadState, setLoadState] = useState<LoadState>("loading");
  const [jobs, setJobs] = useState<LegacyJobSummary[]>([]);
  const [importStatus, setImportStatus] = useState<LegacyImportStatus | null>(null);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [company, setCompany] = useState("");
  const [location, setLocation] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [sourceRoot, setSourceRoot] = useState("");
  const [importing, setImporting] = useState(false);
  const [selected, setSelected] = useState<LegacyJobDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [admitting, setAdmitting] = useState<string | null>(null);
  const [demoLoopMessage, setDemoLoopMessage] = useState("");
  const [demoLoop, setDemoLoop] = useState<DemoLoopResult | null>(null);
  const [demoStory, setDemoStory] = useState<DemoStory | null>(null);
  const [demoBusy, setDemoBusy] = useState(false);
  const [manualEdits, setManualEdits] = useState<Record<string, string>>({});
  const demoMode = window.__ACH_CONFIG__?.demoMode === true || import.meta.env.VITE_DEMO_MODE === "true";

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoadState("loading");
    setError("");
    try {
      const [nextStatus, nextJobs] = await Promise.all([
        getLegacyImportStatus(signal),
        listLegacyJobs({ limit: 100 }, signal),
      ]);
      setImportStatus(nextStatus);
      setSourceRoot((current) => current || nextStatus.configured_source_root || "");
      setJobs(nextJobs.length > 0 || !demoMode ? nextJobs : listDemoJobs());
      setLoadState("ready");
    } catch (caught) {
      if (!signal?.aborted) {
        if (demoMode) {
          setJobs(listDemoJobs());
          setError("演示数据已加载；本地职业核心尚未连接，审核操作暂不能保存。检查本地服务后重试。");
          setLoadState("ready");
        } else {
          setError(message(caught));
          setLoadState("error");
        }
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  useEffect(() => {
    if (!demoMode) return;
    const controller = new AbortController();
    getDemoStory(controller.signal).then((story) => {
      if (!controller.signal.aborted && story.available) {
        setDemoStory(story);
        if (story.application_id) setDemoLoop((current) => current ?? ({
          staging_id: story.staging_id ?? "", opportunity_id: story.opportunity_id ?? "",
          application_id: story.application_id!, application_state: "preparing",
          patch_id: story.resume_patches?.[0]?.patch_id ?? null,
          resume_revision_id: story.resume_revision_id ?? "", interview_id: null,
          interview_revision: null, interview_prep_proposal_id: null, interview_feedback_proposal_id: null,
        }));
      }
    }).catch(() => undefined);
    return () => controller.abort();
  }, [demoMode]);

  async function refreshDemoStory() {
    const story = await getDemoStory();
    setDemoStory(story);
    return story;
  }

  async function reviewDemoPatch(patchId: string, decision: "accepted" | "rejected", edit = false) {
    if (!demoLoop) return;
    setDemoBusy(true);
    setDemoLoopMessage("正在保存审核决定…");
    try {
      await approveDemoResume(patchId, demoLoop.application_id, decision, edit ? manualEdits[patchId] : undefined);
      const story = await refreshDemoStory();
      setDemoLoopMessage("审核已写入本地演示数据库，可在历史与知识页查看。");
      if (!story.resume_patches?.some((patch) => patch.review_status === "proposed")) {
        setDemoLoopMessage("所有修改已审核。确认后可生成独立目标简历版本。");
      }
    } catch (caught) {
      setDemoLoopMessage(`${message(caught)} 可重试；页面将从数据库重新读取审核状态。`);
      try { await refreshDemoStory(); } catch { /* Keep the explicit save error visible. */ }
    } finally {
      setDemoBusy(false);
    }
  }

  async function searchJobs(event?: FormEvent<HTMLFormElement>) {
    event?.preventDefault();
    setLoadState("loading");
    setError("");
    try {
      const nextJobs = await listLegacyJobs({
          query: query.trim(),
          company: company.trim(),
          location: location.trim(),
          status: statusFilter,
          limit: 100,
        });
      setJobs(nextJobs.length > 0 || !demoMode ? nextJobs : listDemoJobs());
      setLoadState("ready");
    } catch (caught) {
      if (demoMode) {
        const queryText = query.trim().toLowerCase();
        setJobs(listDemoJobs().filter((job) => `${job.title} ${job.company} ${job.tags.join(" ")}`.toLowerCase().includes(queryText)));
        setError("当前为离线演示搜索，结果来自脱敏历史样本。");
        setLoadState("ready");
      } else {
        setError(message(caught));
        setLoadState("error");
      }
    }
  }

  async function importHistory() {
    setImporting(true);
    setError("");
    try {
      const report = await runLegacyImport(sourceRoot.trim() || undefined);
      setImportStatus((current) => ({
        configured_source_root: sourceRoot.trim() || current?.configured_source_root || null,
        source_accessible: true,
        latest_report: report,
      }));
      await searchJobs();
    } catch (caught) {
      setError(message(caught));
    } finally {
      setImporting(false);
    }
  }

  async function openDetail(job: LegacyJobSummary) {
    setDetailLoading(true);
    setError("");
    try {
      if (demoMode) {
        const demo = getDemoJob(job.staging_id);
        setSelected(demo ? { job: demo, jd_text: "演示数据包未公开完整 JD；仅展示结构化岗位摘要与技能标签。", raw_record: {}, transform: {}, batch_id: "demo-v1", related_interviews: [] } : null);
      } else {
        setSelected(await getLegacyJob(job.staging_id));
      }
    } catch (caught) {
      setError(message(caught));
    } finally {
      setDetailLoading(false);
    }
  }

  async function admit(job: LegacyJobSummary) {
    setAdmitting(job.staging_id);
    setError("");
    try {
      await admitStagedJob(job.staging_id);
      await searchJobs();
      if (selected?.job.staging_id === job.staging_id) {
        setSelected(await getLegacyJob(job.staging_id));
      }
    } catch (caught) {
      setError(message(caught));
    } finally {
      setAdmitting(null);
    }
  }

  const report = importStatus?.latest_report;
  const importedJobCount = useMemo(
    () => jobs.filter((item) => item.review_status !== "duplicate").length,
    [jobs],
  );

  return (
    <section className="radar-panel legacy-jobs" aria-labelledby="legacy-jobs-title">
      <div className="section-heading legacy-jobs__heading">
        <div>
          <p className="eyebrow">本地历史数据</p>
          <h2 id="legacy-jobs-title">历史岗位库</h2>
          <p>从只读 Agent Radar 导入；导入记录不是个人事实，也不会自动进入求职流程。</p>
        </div>
        <div className="legacy-jobs__summary" aria-label="历史岗位概况">
          <strong>{report?.totals.read_count ?? importedJobCount}</strong>
          <span>{report ? "条源记录" : "条可见岗位"}</span>
        </div>
        {demoMode && (
          <button
            className="primary-command"
            type="button"
            onClick={() => {
              setDemoLoopMessage("正在保存演示闭环…");
              setDemoBusy(true);
              void startDemoLoop()
                .then((result) => {
                  setDemoLoop(result);
                  setDemoLoopMessage(`已创建准备中申请 ${result.application_id}；请逐条审核岗位目标简历草稿。`);
                  return refreshDemoStory();
                })
                .catch((caught) => setDemoLoopMessage(message(caught)))
                .finally(() => setDemoBusy(false));
            }}
            disabled={demoBusy}
          >
            开始演示闭环
          </button>
        )}
      </div>
      {demoMode && demoStory?.resume_patches?.length ? <section className="today-panel" aria-label="简历修改审核">
        <h3>目标简历草稿 · 本地演示 / 待人工审核</h3>
        <p>岗位：{demoStory.opportunity_id ?? "尚未建立关联"} · 申请：{demoStory.application_id ?? "尚未建立关联"} · 状态：{demoStory.application_state ?? "尚未建立关联"}</p>
        <h4>岗位要求与来源</h4>
        {demoStory.requirements?.length ? <ul>{demoStory.requirements.map((requirement) => <li key={requirement.requirement_id}>{requirement.requirement_text} · {requirement.requirement_id} · {requirement.status}</li>)}</ul> : <p>JD 要求：尚未建立关联</p>}
        <p>岗位 Evidence：{demoStory.evidence_ref_id ?? "尚未建立关联"}</p>
        <p>基础简历保持不变。岗位来源 Evidence 只说明岗位上下文，不证明个人经历或技能。</p>
        {demoStory.resume_patches.map((patch) => <article key={patch.patch_id}>
          <h4>Patch {patch.patch_id} · {patch.review_status === "proposed" ? "待审核" : patch.review_status === "accepted" ? "已接受" : "已拒绝"}</h4>
          {patch.operations.map((operation, index) => <div key={`${patch.patch_id}-${index}`}>
            <p>修改前：{JSON.stringify(operation.before)} → 建议：{JSON.stringify(operation.after)}</p>
            <p>{operation.reason} · JD 要求：{operation.requirement_ids.join("、") || "尚未建立关联"} · Evidence：{operation.evidence_ids.join("、") || "尚未建立关联"}</p>
            {patch.review_status === "proposed" && <label>手动编辑（用户内容）<textarea value={manualEdits[patch.patch_id] ?? String(operation.after ?? "")} onChange={(event) => setManualEdits((current) => ({ ...current, [patch.patch_id]: event.target.value }))} /></label>}
          </div>)}
          <p>{patch.review_source} {patch.reviewed_at ? `· ${patch.reviewed_at}` : ""} {patch.review_note ? `· ${patch.review_note}` : ""}</p>
          {patch.review_status === "proposed" && <div className="button-row">
            <button type="button" disabled={demoBusy} onClick={() => void reviewDemoPatch(patch.patch_id, "accepted")}>接受</button>
            <button type="button" disabled={demoBusy} onClick={() => void reviewDemoPatch(patch.patch_id, "rejected")}>拒绝</button>
            <button type="button" disabled={demoBusy} onClick={() => void reviewDemoPatch(patch.patch_id, "accepted", true)}>保存手动编辑并接受</button>
          </div>}
        </article>)}
        {demoLoop && demoStory.resume_patches.every((patch) => patch.review_status !== "proposed") && !demoStory.resume_revision_id && <button type="button" disabled={demoBusy} onClick={() => {
          setDemoBusy(true); setDemoLoopMessage("正在生成不可覆盖的目标简历版本…");
          void createDemoResumeRevision(demoLoop.application_id).then(async (result) => {
            setDemoLoopMessage(`已持久化 ${result.resume_revision_id}，申请仍处于准备中。`);
            await refreshDemoStory();
          }).catch((caught) => setDemoLoopMessage(`${message(caught)} 请检查审核项后重试。`)).finally(() => setDemoBusy(false));
        }}>生成目标 ResumeRevision</button>}
        {demoStory.resume_revision_id && <p>已生成版本：{demoStory.resume_revision_id} · 申请：{demoStory.application_id} · 状态仍为准备中</p>}
        <nav aria-label="演示追溯页面"><Link to="/history">申请与历史</Link> · <Link to="/resume">简历版本</Link> · <Link to="/knowledge">知识追溯</Link></nav>
      </section> : null}
      {demoLoopMessage && <p className="inline-status" role="status">{demoLoopMessage}</p>}

      <div className="legacy-import-bar">
        <label>
          <span>旧版 Agent Radar 数据目录</span>
          <input
            aria-label="旧版 Agent Radar 数据目录"
            value={sourceRoot}
            onChange={(event) => setSourceRoot(event.target.value)}
            placeholder="请选择或输入旧 Agent Radar 目录"
          />
        </label>
        <button
          className="secondary-command"
          type="button"
          onClick={() => void importHistory()}
          disabled={importing || !sourceRoot.trim()}
        >
          <Upload size={16} aria-hidden="true" />
          {importing ? "正在核验并导入…" : report ? "重新核验导入" : "导入历史数据"}
        </button>
        {report && (
          <div className="legacy-import-result">
            <Database size={16} aria-hidden="true" />
            <span>
              最近批次：读取 {report.totals.read_count ?? 0} · 新增 {report.totals.new_count ?? 0}
              {" · "}重复 {report.totals.duplicate_count ?? 0} · 失败 {report.totals.failed_count ?? 0}
            </span>
          </div>
        )}
      </div>

      <form className="legacy-job-filters" onSubmit={(event) => void searchJobs(event)}>
        <label className="legacy-job-filters__query">
          <span>搜索岗位、公司或技能</span>
          <div>
            <Search size={16} aria-hidden="true" />
            <input
              aria-label="搜索岗位、公司或技能"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="例如：Python、推荐系统、字节跳动"
            />
          </div>
        </label>
        <label>
          <span>公司</span>
          <input value={company} onChange={(event) => setCompany(event.target.value)} />
        </label>
        <label>
          <span>地点</span>
          <input value={location} onChange={(event) => setLocation(event.target.value)} />
        </label>
        <label>
          <span>状态</span>
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)}>
            <option value="">全部状态</option>
            <option value="staged">待选择</option>
            <option value="duplicate">重复待复核</option>
            <option value="admitted">已加入求职流程</option>
            <option value="rejected">已忽略</option>
          </select>
        </label>
        <button className="primary-command" type="submit">
          <Search size={16} aria-hidden="true" />搜索
        </button>
      </form>

      {error && (
        <p className="inline-error radar-error" role="alert">
          <AlertCircle size={16} aria-hidden="true" />
          {error}
          <button className="secondary-command" type="button" onClick={() => void load()}>
            <RefreshCw size={14} aria-hidden="true" />重试
          </button>
        </p>
      )}

      {loadState === "loading" && (
        <div className="radar-state" aria-live="polite">
          <span className="status-spinner" aria-hidden="true" />
          <p>正在读取历史岗位…</p>
        </div>
      )}

      {loadState === "ready" && jobs.length === 0 && (
        <div className="radar-state legacy-jobs__empty">
          <Inbox size={24} aria-hidden="true" />
          <h3>还没有可展示的历史岗位</h3>
          <p>确认上方 Legacy 数据目录后点击“导入历史数据”，或调整搜索条件。</p>
        </div>
      )}

      {loadState === "ready" && jobs.length > 0 && (
        <div className="legacy-job-layout">
          <div className="legacy-job-list" aria-label={`历史岗位，共 ${jobs.length} 条`}>
            <div className="legacy-job-list__count">当前显示 {jobs.length} 条</div>
            {jobs.map((job) => (
              <article
                className={`legacy-job-card${selected?.job.staging_id === job.staging_id ? " is-selected" : ""}`}
                key={job.staging_id}
              >
                <button type="button" className="legacy-job-card__main" onClick={() => void openDetail(job)}>
                  <div className="legacy-job-card__title">
                    <h3>{job.title}</h3>
                    <span className={`record-status record-status--${job.status}`}>
                      {statusLabels[job.status]}
                    </span>
                  </div>
                  <p><Building2 size={14} aria-hidden="true" />{job.company}</p>
                  <p><MapPin size={14} aria-hidden="true" />{displayText(job.location) || "地点未记录"}{job.salary ? ` · ${job.salary}` : ""}</p>
                  {displayTags(job.tags).length > 0 && (
                    <div className="legacy-job-tags">
                      {displayTags(job.tags).map((tag) => <span key={tag}>{tag}</span>)}
                    </div>
                  )}
                  <small>{reviewLabels[job.review_status]} · {sourceClassLabels[job.source_class] ?? "历史来源"}</small>
                </button>
                <div className="legacy-job-card__actions">
                  <button className="secondary-command" type="button" onClick={() => void openDetail(job)}>
                    <FileText size={15} aria-hidden="true" />查看详情
                  </button>
                  {job.status === "staged" && (
                    <button
                      className="primary-command"
                      type="button"
                      disabled={admitting === job.staging_id}
                      onClick={() => void admit(job)}
                    >
                      <Check size={15} aria-hidden="true" />
                      {admitting === job.staging_id ? "正在加入…" : "加入求职流程"}
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>

          <aside className="legacy-job-detail" aria-label="岗位详情">
            {detailLoading && <div className="radar-state"><span className="status-spinner" /><p>正在读取岗位详情…</p></div>}
            {!detailLoading && !selected && (
              <div className="radar-state">
                <FileText size={22} aria-hidden="true" />
                <p>选择一个岗位，查看 JD、来源证据和关联面试。</p>
              </div>
            )}
            {!detailLoading && selected && (
              <>
                <header>
                  <div>
                    <p className="eyebrow">岗位详情</p>
                    <h3>{selected.job.title}</h3>
                    <p>{selected.job.company} · {displayText(selected.job.location) || "地点未记录"}</p>
                  </div>
                  <button className="icon-command" type="button" aria-label="关闭岗位详情" onClick={() => setSelected(null)}>
                    <X size={17} aria-hidden="true" />
                  </button>
                </header>
                <section>
                  <h4>职位描述</h4>
                  <div className="legacy-job-jd">{displayJd(selected.jd_text) || "源记录未提供完整 JD 文本。"}</div>
                  {selected.job.source_url && (
                    <a href={selected.job.source_url} target="_blank" rel="noreferrer">
                      查看原始来源 <ExternalLink size={14} aria-hidden="true" />
                    </a>
                  )}
                </section>
                <section>
                  <h4>来源与溯源</h4>
                  <dl className="legacy-provenance">
                    <div><dt>源文件</dt><dd>{selected.job.source_path}</dd></div>
                    <div><dt>行号</dt><dd>{selected.job.row_number}</dd></div>
                    <div><dt>SHA-256</dt><dd title={selected.job.source_sha256}>{shortHash(selected.job.source_sha256)}</dd></div>
                    <div><dt>导入批次</dt><dd>{selected.batch_id}</dd></div>
                    <div><dt>复核状态</dt><dd>{reviewLabels[selected.job.review_status]}</dd></div>
                  </dl>
                </section>
                <section>
                  <h4>关联面试信息</h4>
                  {selected.related_interviews.length === 0 ? (
                    <p className="muted-copy">暂未找到公司与岗位同时匹配的历史面试记录。</p>
                  ) : (
                    <ul className="legacy-interviews">
                      {selected.related_interviews.map((item, index) => (
                        <li key={`${index}-${interviewLabel(item)}`}>{interviewLabel(item)}</li>
                      ))}
                    </ul>
                  )}
                </section>
              </>
            )}
          </aside>
        </div>
      )}
    </section>
  );
}
