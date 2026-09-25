import { Check, FileDown, Palette, ShieldCheck, X } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import {
  createTargetProfile,
  createResumeRevision,
  downloadRenderArtifact,
  getAtsReport,
  listResumeTemplates,
  proposeResumePatch,
  renderResume,
  reviewResumeRender,
  reviewResumePatch,
  validateResumeContent,
  type ResumeAtsReport,
  type ResumeRenderRun,
  type ResumeRenderReview,
  type ResumeTemplate,
} from "../api/resumeStudio";
import { getResumeRevision, listResumeBases, listResumeRevisions } from "../api/projectResume";
import type { ResumeBaseRead, ResumeRevisionRead } from "../api/projectResume";
import { listJobRequirements, type JobRequirement } from "../api/jobRadar";
import { listOpportunities, type OpportunitySummary } from "../api/client";
import { atsStatusLabels, decisionLabels, displayLabel, rendererLabels } from "../app/displayLabels";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";

const DRAFT_KEY = "ach.resume-studio.draft.v1";

function canonicalJson(value: unknown): string {
  if (Array.isArray(value)) return `[${value.map(canonicalJson).join(",")}]`;
  if (value !== null && typeof value === "object") {
    const entries = Object.entries(value as Record<string, unknown>).sort(([a], [b]) => a.localeCompare(b));
    return `{${entries.map(([key, item]) => `${JSON.stringify(key)}:${canonicalJson(item)}`).join(",")}}`;
  }
  return JSON.stringify(value);
}

async function valueHash(value: unknown): Promise<string> {
  const bytes = new TextEncoder().encode(canonicalJson(value));
  const digest = await window.crypto.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(digest), (item) => item.toString(16).padStart(2, "0")).join("");
}

function localId(prefix: string): string {
  return `${prefix}_${window.crypto.randomUUID().replaceAll("-", "")}`;
}

function templateDisplayName(name: string): string {
  return name.replaceAll("Warm Paper", "暖纸");
}

export function ResumeStudioPanel() {
  const [resumeId, setResumeId] = useState("");
  const [revisionId, setRevisionId] = useState("");
  const [resumeBases, setResumeBases] = useState<ResumeBaseRead[]>([]);
  const [resumeRevisions, setResumeRevisions] = useState<ResumeRevisionRead[]>([]);
  const [profileId, setProfileId] = useState("");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [opportunities, setOpportunities] = useState<OpportunitySummary[]>([]);
  const [opportunityId, setOpportunityId] = useState("");
  const [opportunityRequirements, setOpportunityRequirements] = useState<JobRequirement[]>([]);
  const [opportunityLoading, setOpportunityLoading] = useState(false);
  const [templateId, setTemplateId] = useState("resume-render-html");
  const [templates, setTemplates] = useState<ResumeTemplate[]>([
    {
      template_id: "resume-render-html",
      name: "观复简历 / 暖纸",
      version: "1.0.0",
      renderer: "html_css",
      content_sha256: "",
      description: "内置本地渲染器",
      status: "active",
      created_at: "",
    },
  ]);
  const [draftContent, setDraftContent] = useState("");
  const [draftHistory, setDraftHistory] = useState<string[]>([]);
  const [draftFuture, setDraftFuture] = useState<string[]>([]);
  const [loadedRevision, setLoadedRevision] = useState<ResumeRevisionRead | null>(null);
  const [evidenceRef, setEvidenceRef] = useState("");
  const [previewTheme, setPreviewTheme] = useState("warm-paper");
  const [run, setRun] = useState<ResumeRenderRun | null>(null);
  const [report, setReport] = useState<ResumeAtsReport | null>(null);
  const [review, setReview] = useState<ResumeRenderReview | null>(null);
  const [reviewReason, setReviewReason] = useState("");
  const [message, setMessage] = useState("从已审核的简历修订开始渲染。");
  const [validationMessage, setValidationMessage] = useState("");

  useEffect(() => {
    const raw = window.localStorage.getItem(DRAFT_KEY);
    if (raw) {
      try {
        const draft = JSON.parse(raw) as Record<string, string>;
        setResumeId(draft.resumeId || "");
        setRevisionId(draft.revisionId || "");
        setProfileId(draft.profileId || "");
        setTitle(draft.title || "");
        setCompany(draft.company || "");
        setOpportunityId(draft.opportunityId || "");
        setTemplateId(draft.templateId || "resume-render-html");
        setDraftContent(draft.draftContent || "");
        setEvidenceRef(draft.evidenceRef || "");
        setPreviewTheme(draft.previewTheme || "warm-paper");
      } catch {
        window.localStorage.removeItem(DRAFT_KEY);
      }
    }
  }, []);

  async function loadTemplates() {
    try {
      setTemplates(await listResumeTemplates());
    } catch (error) {
      setMessage("模板目录读取失败：" + (error as Error).message);
    }
  }

  async function loadResumeChoices() {
    try {
      const bases = await listResumeBases();
      setResumeBases(bases);
      setMessage(bases.length ? "已读取本地简历档案。" : "还没有基础简历，请先导入或创建简历。");
    } catch {
      setMessage("简历列表读取失败，请检查本地服务后重试。");
    }
  }

  async function selectResume(id: string) {
    setResumeId(id);
    setRevisionId("");
    setResumeRevisions([]);
    if (!id) return;
    setProfileId((current) => current || localId("target_profile"));
    try {
      const revisions = await listResumeRevisions(id);
      setResumeRevisions(revisions);
      if (revisions[0]) setRevisionId(revisions[0].revision_id);
      setMessage(revisions.length ? "已载入该简历的修订版本。" : "此简历尚无已审核修订。");
    } catch {
      setMessage("简历修订列表读取失败，请重试。");
    }
  }

  useEffect(() => {
    window.localStorage.setItem(
      DRAFT_KEY,
      JSON.stringify({
        resumeId,
        revisionId,
        profileId,
        title,
        company,
        templateId,
        draftContent,
        evidenceRef,
        previewTheme,
        opportunityId,
      }),
    );
  }, [resumeId, revisionId, profileId, title, company, templateId, draftContent, evidenceRef, previewTheme, opportunityId]);

  useEffect(() => {
    setRun(null);
    setReport(null);
    setReview(null);
    setReviewReason("");
  }, [revisionId, profileId, templateId]);

  const parsedDraft = useMemo(() => {
    if (!draftContent.trim()) return null;
    try {
      return JSON.parse(draftContent) as Record<string, unknown>;
    } catch {
      return null;
    }
  }, [draftContent]);

  function updateDraftContent(next: string) {
    setDraftContent((current) => {
      if (current === next) return current;
      setDraftHistory((history) => [...history.slice(-49), current]);
      setDraftFuture([]);
      return next;
    });
  }

  function updateTopLevelField(key: string, next: string) {
    if (!parsedDraft) return;
    const current = parsedDraft[key];
    let value: unknown = next;
    if (typeof current === "number") {
      const parsed = Number(next);
      value = Number.isFinite(parsed) ? parsed : next;
    } else if (typeof current === "boolean") {
      value = next === "true";
    } else if (current === null) {
      value = next || null;
    }
    updateDraftContent(JSON.stringify({ ...parsedDraft, [key]: value }, null, 2));
  }

  function updateArrayItem(key: string, index: number, next: string) {
    if (!parsedDraft || !Array.isArray(parsedDraft[key])) return;
    const values = [...parsedDraft[key] as unknown[]];
    const current = values[index];
    values[index] = current !== null && typeof current === "object" && !Array.isArray(current)
      ? { ...(current as Record<string, unknown>), ["text" in (current as Record<string, unknown>) ? "text" : "title" in (current as Record<string, unknown>) ? "title" : "value"]: next }
      : next;
    updateDraftContent(JSON.stringify({ ...parsedDraft, [key]: values }, null, 2));
  }

  function arrayItemText(value: unknown): string {
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
    if (value !== null && typeof value === "object") {
      const record = value as Record<string, unknown>;
      const candidate = record.text ?? record.title ?? record.name ?? record.value;
      if (typeof candidate === "string" || typeof candidate === "number" || typeof candidate === "boolean") return String(candidate);
    }
    return JSON.stringify(value);
  }

  function undoDraft() {
    setDraftHistory((history) => {
      const previous = history.at(-1);
      if (previous === undefined) return history;
      setDraftContent((current) => {
        setDraftFuture((future) => [...future.slice(-49), current]);
        return previous;
      });
      return history.slice(0, -1);
    });
  }

  function redoDraft() {
    setDraftFuture((future) => {
      const next = future.at(-1);
      if (next === undefined) return future;
      setDraftContent((current) => {
        setDraftHistory((history) => [...history.slice(-49), current]);
        return next;
      });
      return future.slice(0, -1);
    });
  }

  async function loadRevisionDraft() {
    try {
      const revision = await getResumeRevision(revisionId);
      setLoadedRevision(revision);
      setRun(null);
      setReport(null);
      setReview(null);
      setReviewReason("");
      setDraftContent(JSON.stringify(revision.content, null, 2));
      setDraftHistory([]);
      setDraftFuture([]);
      setMessage("已加载为本地提案草稿；修改不会写回职业核心。");
    } catch (error) {
      setMessage("版本读取失败：" + (error as Error).message);
    }
  }

  async function promoteDraft() {
    if (!loadedRevision || !parsedDraft || !profileId || !evidenceRef.trim()) return;
    try {
      const previous = loadedRevision.content;
      const previousKeys = Object.keys(previous).sort();
      if (Object.keys(parsedDraft).sort().join("\0") !== previousKeys.join("\0")) {
        throw new Error("当前编辑器只允许修改现有顶层字段；新增或删除字段需专门 patch UI。 ");
      }
      const operations = [];
      for (const key of previousKeys) {
        if (canonicalJson(previous[key]) === canonicalJson(parsedDraft[key])) continue;
        operations.push({
          action: "set",
          target_path: `/${key.replaceAll("~", "~0").replaceAll("/", "~1")}`,
          expected_value_hash: await valueHash(previous[key]),
          proposed_value: parsedDraft[key],
          evidence_refs: [evidenceRef.trim()],
          reason: "用户编辑的本地草稿，由明确的证据引用支持。",
        });
      }
      if (operations.length === 0) throw new Error("草稿与已加载 revision 没有差异。");
      const patchId = localId("resume_patch");
      const proposalCommand = localId("command_resume_patch_propose");
      const proposal = await proposeResumePatch({
        command_id: proposalCommand,
        patch_id: patchId,
        target_profile_id: profileId,
        resume_id: loadedRevision.resume_id,
        base_revision: loadedRevision.base_revision,
        operations,
        actor: "agent:resume-studio",
      }, `resume-studio-${proposalCommand}`);
      const reviewCommand = localId("command_resume_patch_review");
      const accepted = await reviewResumePatch(patchId, {
        command_id: reviewCommand,
        expected_revision: proposal.revision,
        decision: "accepted",
        review_reason: "用户已核对可见的本地草稿修改。",
      }, `resume-studio-${reviewCommand}`);
      const revisionCommand = localId("command_resume_revision");
      const revision = await createResumeRevision({
        command_id: revisionCommand,
        resume_id: loadedRevision.resume_id,
        base_revision: loadedRevision.base_revision,
        accepted_patch_refs: [
          ...loadedRevision.accepted_patch_refs,
          { entity_id: patchId, revision: accepted.revision },
        ],
      }, `resume-studio-${revisionCommand}`);
      setRevisionId(revision.revision_id);
      setLoadedRevision(null);
      setMessage("草稿已由用户审核并生成新的不可变简历修订；现在可正式渲染。");
    } catch (error) {
      setMessage("草稿提交失败：" + (error as Error).message);
    }
  }

  async function validateDraft() {
    if (!parsedDraft) {
      setValidationMessage("请先输入有效的 JSON 简历内容。");
      return;
    }
    try {
      const result = await validateResumeContent(parsedDraft);
      setValidationMessage(result.valid
        ? (result.warnings.length ? `格式有效：${result.warnings.join("；")}` : "简历结构校验通过。")
        : `校验失败：${result.errors.join("；")}`);
    } catch (error) {
      setValidationMessage("简历校验失败：" + (error as Error).message);
    }
  }

  async function saveProfile() {
    setMessage("正在保存目标岗位…");
    try {
      const profile = await createTargetProfile({
        target_profile_id: profileId,
        resume_id: resumeId,
        title,
        company: company || undefined,
        opportunity_id: opportunityId || undefined,
        opportunity_revision: selectedOpportunity?.opportunity.revision,
        requirement_refs: opportunityRequirements
          .filter((item) => item.status === "accepted")
          .map((item) => ({ entity_id: item.requirement_id, revision: item.revision })),
      });
      setProfileId(profile.target_profile_id);
      setMessage("目标岗位已保存为用户确认的目标岗位档案。");
    } catch (error) {
      setMessage("目标岗位保存失败：" + (error as Error).message);
    }
  }

  const selectedOpportunity = opportunities.find(
    (item) => item.opportunity.entity_id === opportunityId,
  );

  async function loadOpportunities() {
    if (opportunities.length || opportunityLoading) return;
    setOpportunityLoading(true);
    try {
      setOpportunities(await listOpportunities());
    } catch {
      setMessage("岗位机会读取失败，请检查本地服务后重试。");
    } finally {
      setOpportunityLoading(false);
    }
  }

  async function selectOpportunity(id: string) {
    setOpportunityId(id);
    setOpportunityRequirements([]);
    const selected = opportunities.find((item) => item.opportunity.entity_id === id);
    if (!selected) return;
    try {
      const requirements = await listJobRequirements(selected.job.job_id, selected.job.revision);
      setOpportunityRequirements(requirements);
      setTitle((current) => current || selected.job.job_id);
      setMessage(requirements.some((item) => item.status === "accepted")
        ? "已载入岗位版本与已审核要求。"
        : "该岗位版本暂无已审核要求，保存前请先完成 JD 审核。 ");
    } catch {
      setMessage("岗位要求读取失败，请重试。");
    }
  }

  async function render() {
    setMessage("正在生成 HTML 预览与 PDF…");
    try {
      const rendered = await renderResume({
        resume_revision_id: revisionId,
        target_profile_id: profileId || undefined,
        template_id: templateId,
      });
      setRun(rendered);
      setReview(null);
      setReport(await getAtsReport(rendered.render_run_id));
      setMessage("生成完成；输出仍是不可变 Artifact，需人工审核后用于申请。");
    } catch (error) {
      setMessage("渲染失败：" + (error as Error).message);
    }
  }

  async function submitReview(decision: "approved" | "rejected") {
    if (!run || !reviewReason.trim()) return;
    try {
      const saved = await reviewResumeRender(run.render_run_id, {
        decision,
        reason: reviewReason.trim(),
      });
      setReview(saved);
      setMessage(`用户审核已记录：${displayLabel(saved.decision, decisionLabels)}。输出文件本身保持不可变。`);
    } catch (error) {
      setMessage("审核记录失败：" + (error as Error).message);
    }
  }

  async function download() {
    if (!run) return;
    try {
      const blob = await downloadRenderArtifact(run.render_run_id);
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `${run.render_run_id}.pdf`;
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (error) {
      setMessage("PDF 下载失败：" + (error as Error).message);
    }
  }

  return (
    <section className="resume-studio" aria-label="简历工作室">
      <div className="resume-studio__head">
        <div>
          <span className="eyebrow">简历工作室</span>
          <h2>目标岗位定制与预览</h2>
        </div>
        <span className="badge"><Palette size={12} aria-hidden="true" />观复模板</span>
      </div>
      <div className="resume-studio-grid">
        <Field label="基础简历"><select className="select" aria-label="基础简历" value={resumeId} onFocus={() => void loadResumeChoices()} onChange={(event) => void selectResume(event.target.value)}><option value="">请选择简历</option>{resumeBases.map((base, index) => <option key={base.resume_id} value={base.resume_id}>我的简历 {index + 1} · 第 {base.revision} 版</option>)}</select></Field>
        <Field label="已审核修订"><select className="select" aria-label="已审核修订" value={revisionId} onChange={(event) => setRevisionId(event.target.value)}><option value="">请选择修订</option>{resumeRevisions.map((revision) => <option key={revision.revision_id} value={revision.revision_id}>{revision.revision_id} · 第 {revision.base_revision} 版基础简历</option>)}</select></Field>
        <Field label="目标岗位档案精确引用"><input className="input" value={profileId} onChange={(event) => setProfileId(event.target.value)} placeholder="输入高级引用" /></Field>
        <Field label="绑定机会版本"><select className="select" aria-label="绑定机会版本" value={opportunityId} onFocus={() => void loadOpportunities()} onChange={(event) => void selectOpportunity(event.target.value)}><option value="">请选择已录入岗位</option>{opportunities.map((item) => <option key={item.opportunity.entity_id} value={item.opportunity.entity_id}>{item.opportunity.entity_id} · 岗位 {item.job.job_id} · v{item.opportunity.revision}</option>)}</select></Field>
        <Field label="目标岗位"><input className="input" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="例如：平台工程师" /></Field>
        <Field label="公司（可选）"><input className="input" value={company} onChange={(event) => setCompany(event.target.value)} placeholder="例如：目标公司" /></Field>
        <Field label="渲染模板"><select className="select" aria-label="渲染模板" value={templateId} onFocus={loadTemplates} onChange={(event) => setTemplateId(event.target.value)}>
          {templates.map((template) => <option key={template.template_id} value={template.template_id} disabled={template.status !== "active"}>{templateDisplayName(template.name)} · {displayLabel(template.renderer, rendererLabels)}{template.status === "disabled" ? "（不可用）" : ""}</option>)}
        </select></Field>
      </div>
      {selectedOpportunity && <div className="text-aux" aria-label="岗位证据绑定"><p>岗位版本：{selectedOpportunity.job.job_id}#{selectedOpportunity.job.revision} · 机会版本：{selectedOpportunity.opportunity.revision}</p><p>已审核要求：{opportunityRequirements.filter((item) => item.status === "accepted").length} 条（保存目标岗位时将精确引用）</p></div>}
      <div className="button-row">
        <button className="btn btn--secondary" type="button" onClick={saveProfile} disabled={!resumeId || !profileId || !title}>保存目标岗位</button>
        <button className="btn btn--secondary" type="button" onClick={loadRevisionDraft} disabled={!revisionId}>加载到本地草稿</button>
        <button className="btn btn--primary" type="button" onClick={render} disabled={!revisionId}>生成预览与 PDF</button>
      </div>
      <p className="text-aux" role="status">{message}</p>
      <div className="resume-draft-workspace">
        <div>{parsedDraft && <div className="resume-field-editor" aria-label="简历字段编辑"><strong>字段编辑</strong>{Object.entries(parsedDraft).filter(([, value]) => value === null || ["string", "number", "boolean"].includes(typeof value)).map(([key, value]) => <Field key={key} label={key}><input className="input" aria-label={`简历字段 ${key}`} value={value === null ? "" : String(value)} onChange={(event) => updateTopLevelField(key, event.target.value)} /></Field>)}{Object.entries(parsedDraft).filter(([, value]) => Array.isArray(value)).map(([key, value]) => <fieldset className="resume-array-editor" key={key}><legend>{key}</legend>{(value as unknown[]).map((item, index) => <Field label={`${key} 第 ${index + 1} 项`} key={`${key}:${index}`}><input className="input" aria-label={`简历字段 ${key} 第 ${index + 1} 项`} value={arrayItemText(item)} onChange={(event) => updateArrayItem(key, index, event.target.value)} /></Field>)}</fieldset>)}</div>}<Field label="建议草稿（JSON，本地自动保存）"><textarea className="textarea resume-studio__editor" aria-label="简历建议草稿" value={draftContent} onChange={(event) => updateDraftContent(event.target.value)} placeholder={'{\n  "summary": "…"\n}'} /></Field><div className="button-row"><button className="btn btn--secondary" type="button" onClick={undoDraft} disabled={draftHistory.length === 0}>撤销</button><button className="btn btn--secondary" type="button" onClick={redoDraft} disabled={draftFuture.length === 0}>重做</button><button className="btn btn--secondary" type="button" onClick={() => void validateDraft()} disabled={!parsedDraft}>校验简历结构</button><button className="btn btn--primary" type="button" onClick={promoteDraft} disabled={!loadedRevision || !parsedDraft || !profileId || !evidenceRef.trim()}>审核草稿并创建新修订</button></div>{validationMessage && <p role="status">{validationMessage}</p>}<Field label="证据精确引用"><input className="input" aria-label="草稿证据精确引用" value={evidenceRef} onChange={(event) => setEvidenceRef(event.target.value)} placeholder="输入证据引用" /></Field></div>
        <div>
          <Field label="预览主题"><select className="select" aria-label="预览主题" value={previewTheme} onChange={(event) => setPreviewTheme(event.target.value)}><option value="warm-paper">暖纸</option><option value="compact-ink">紧凑墨色</option></select></Field>
          <article className={`resume-draft-preview ${previewTheme}`} aria-label="草稿实时预览">
            {parsedDraft ? Object.entries(parsedDraft).map(([key, value]) => <section key={key}><strong>{key}</strong><p>{typeof value === "string" ? value : JSON.stringify(value)}</p></section>) : <p>{draftContent ? "JSON 格式无效" : "尚未加载草稿"}</p>}
          </article>
        </div>
      </div>
      {run && (
        <div className="resume-studio-output">
          <div className="resume-studio-output-heading">
            <h3>预览</h3>
            <Button size="sm" variant="secondary" onClick={() => void download()} icon={<FileDown size={13} aria-hidden="true" />}>下载 PDF</Button>
          </div>
          <div className="resume-preview" dangerouslySetInnerHTML={{ __html: run.preview_html }} />
          {report && (
            <div className="resume-ats-report">
              <span><ShieldCheck size={14} /> ATS：{displayLabel(report.status, atsStatusLabels)}</span>
              <span>{report.page_count} 页</span>
              {report.keyword_gaps.length > 0 && <span>Gap：{report.keyword_gaps.join("、")}</span>}
            </div>
          )}
          <div className="resume-render-review">
            <strong>导出文件人工审核</strong>
            <p>生成物不会自动成为简历事实或申请用最终稿。</p>
            <Field label="审核理由"><input className="input" aria-label="审核理由" value={reviewReason} onChange={(event) => setReviewReason(event.target.value)} disabled={Boolean(review)} /></Field>
            <div className="button-row">
              <button className="btn btn--secondary" type="button" onClick={() => submitReview("rejected")} disabled={!reviewReason.trim() || Boolean(review)}><X size={14} />拒绝</button>
              <button className="btn btn--primary" type="button" onClick={() => submitReview("approved")} disabled={!reviewReason.trim() || Boolean(review)}><Check size={14} />批准</button>
            </div>
            {review && <span className="badge badge--green">已由用户{displayLabel(review.decision, decisionLabels)}</span>}
          </div>
        </div>
      )}
    </section>
  );
}
