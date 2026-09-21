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
  type ResumeAtsReport,
  type ResumeRenderRun,
  type ResumeRenderReview,
  type ResumeTemplate,
} from "../api/resumeStudio";
import { getResumeRevision } from "../api/projectResume";
import type { ResumeRevisionRead } from "../api/projectResume";

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

export function ResumeStudioPanel() {
  const [resumeId, setResumeId] = useState("");
  const [revisionId, setRevisionId] = useState("");
  const [profileId, setProfileId] = useState("");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [templateId, setTemplateId] = useState("resume-render-html");
  const [templates, setTemplates] = useState<ResumeTemplate[]>([
    {
      template_id: "resume-render-html",
      name: "观复简历 / Warm Paper",
      version: "1.0.0",
      renderer: "html_css",
      content_sha256: "",
      description: "Built-in local renderer",
      status: "active",
      created_at: "",
    },
  ]);
  const [draftContent, setDraftContent] = useState("");
  const [loadedRevision, setLoadedRevision] = useState<ResumeRevisionRead | null>(null);
  const [evidenceRef, setEvidenceRef] = useState("");
  const [previewTheme, setPreviewTheme] = useState("warm-paper");
  const [run, setRun] = useState<ResumeRenderRun | null>(null);
  const [report, setReport] = useState<ResumeAtsReport | null>(null);
  const [review, setReview] = useState<ResumeRenderReview | null>(null);
  const [reviewReason, setReviewReason] = useState("");
  const [message, setMessage] = useState("从已审核的 Resume Revision 开始渲染。");

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
      }),
    );
  }, [resumeId, revisionId, profileId, title, company, templateId, draftContent, evidenceRef, previewTheme]);

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

  async function loadRevisionDraft() {
    try {
      const revision = await getResumeRevision(revisionId);
      setLoadedRevision(revision);
      setRun(null);
      setReport(null);
      setReview(null);
      setReviewReason("");
      setDraftContent(JSON.stringify(revision.content, null, 2));
      setMessage("已加载为本地 proposal draft；修改不会写回 Career Core。");
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
          reason: "User-edited local draft backed by an explicit EvidenceRef.",
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
        review_reason: "User approved the visible local draft changes.",
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
      setMessage("草稿已由用户审核并生成新的 immutable ResumeRevision；现在可正式渲染。");
    } catch (error) {
      setMessage("草稿提交失败：" + (error as Error).message);
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
      });
      setProfileId(profile.target_profile_id);
      setMessage("目标岗位已保存为用户确认的 target profile。");
    } catch (error) {
      setMessage("目标岗位保存失败：" + (error as Error).message);
    }
  }

  async function render() {
    setMessage("正在生成 HTML preview 与 PDF…");
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
      setMessage(`用户审核已记录：${saved.decision}。Artifact 本身保持不可变。`);
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
    <section className="resume-studio panel" aria-label="Resume Studio">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Resume Studio</p>
          <h2>目标岗位定制与预览</h2>
        </div>
        <span className="service-status"><Palette size={15} />观复模板</span>
      </div>
      <div className="resume-studio-grid">
        <label>Studio Resume Base ID<input value={resumeId} onChange={(event) => setResumeId(event.target.value)} placeholder="resume_…" /></label>
        <label>Studio Resume Revision ID<input value={revisionId} onChange={(event) => setRevisionId(event.target.value)} placeholder="resume_revision_…" /></label>
        <label>Target Profile ID<input value={profileId} onChange={(event) => setProfileId(event.target.value)} placeholder="target_profile_…" /></label>
        <label>目标岗位<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Platform Engineer" /></label>
        <label>公司（可选）<input value={company} onChange={(event) => setCompany(event.target.value)} placeholder="Company" /></label>
        <label>渲染模板<select aria-label="渲染模板" value={templateId} onFocus={loadTemplates} onChange={(event) => setTemplateId(event.target.value)}>
          {templates.map((template) => <option key={template.template_id} value={template.template_id} disabled={template.status !== "active"}>{template.name} · {template.renderer}{template.status === "disabled" ? "（不可用）" : ""}</option>)}
        </select></label>
      </div>
      <div className="button-row">
        <button className="button button-secondary" type="button" onClick={saveProfile} disabled={!resumeId || !profileId || !title}>保存目标岗位</button>
        <button className="button button-secondary" type="button" onClick={loadRevisionDraft} disabled={!revisionId}>加载到本地草稿</button>
        <button className="button button-primary" type="button" onClick={render} disabled={!revisionId}>生成预览与 PDF</button>
      </div>
      <p className="resume-studio-message">{message}</p>
      <div className="resume-draft-workspace">
        <div><label>Proposal draft（JSON，本地自动保存）<textarea aria-label="Resume proposal draft" value={draftContent} onChange={(event) => setDraftContent(event.target.value)} placeholder={'{\n  "summary": "…"\n}'} /></label><label>EvidenceRef<input aria-label="Draft EvidenceRef" value={evidenceRef} onChange={(event) => setEvidenceRef(event.target.value)} placeholder="evidence_…" /></label><button className="button button-primary" type="button" onClick={promoteDraft} disabled={!loadedRevision || !parsedDraft || !profileId || !evidenceRef.trim()}>审核草稿并创建新 Revision</button></div>
        <div>
          <label>预览主题<select aria-label="预览主题" value={previewTheme} onChange={(event) => setPreviewTheme(event.target.value)}><option value="warm-paper">暖纸</option><option value="compact-ink">紧凑墨色</option></select></label>
          <article className={`resume-draft-preview ${previewTheme}`} aria-label="草稿实时预览">
            {parsedDraft ? Object.entries(parsedDraft).map(([key, value]) => <section key={key}><strong>{key}</strong><p>{typeof value === "string" ? value : JSON.stringify(value)}</p></section>) : <p>{draftContent ? "JSON 格式无效" : "尚未加载草稿"}</p>}
          </article>
        </div>
      </div>
      {run && (
        <div className="resume-studio-output">
          <div className="resume-studio-output-heading">
            <h3>预览</h3>
            <button className="resume-download" type="button" onClick={download}><FileDown size={14} />下载 PDF</button>
          </div>
          <div className="resume-preview" dangerouslySetInnerHTML={{ __html: run.preview_html }} />
          {report && (
            <div className="resume-ats-report">
              <span><ShieldCheck size={14} /> ATS：{report.status}</span>
              <span>{report.page_count} 页</span>
              {report.keyword_gaps.length > 0 && <span>Gap：{report.keyword_gaps.join("、")}</span>}
            </div>
          )}
          <div className="resume-render-review">
            <strong>Artifact 人工审核</strong>
            <p>生成物不会自动成为 Resume Fact 或申请用最终稿。</p>
            <label>审核理由<input aria-label="审核理由" value={reviewReason} onChange={(event) => setReviewReason(event.target.value)} disabled={Boolean(review)} /></label>
            <div className="button-row">
              <button className="button button-secondary" type="button" onClick={() => submitReview("rejected")} disabled={!reviewReason.trim() || Boolean(review)}><X size={14} />拒绝</button>
              <button className="button button-primary" type="button" onClick={() => submitReview("approved")} disabled={!reviewReason.trim() || Boolean(review)}><Check size={14} />批准</button>
            </div>
            {review && <span className="service-status">已由用户 {review.decision}</span>}
          </div>
        </div>
      )}
    </section>
  );
}
