import { FileDown, Palette, ShieldCheck } from "lucide-react";
import { useState } from "react";

import {
  createTargetProfile,
  downloadRenderArtifact,
  getAtsReport,
  renderResume,
  type ResumeAtsReport,
  type ResumeRenderRun,
} from "../api/resumeStudio";

export function ResumeStudioPanel() {
  const [resumeId, setResumeId] = useState("");
  const [revisionId, setRevisionId] = useState("");
  const [profileId, setProfileId] = useState("");
  const [title, setTitle] = useState("");
  const [company, setCompany] = useState("");
  const [run, setRun] = useState<ResumeRenderRun | null>(null);
  const [report, setReport] = useState<ResumeAtsReport | null>(null);
  const [message, setMessage] = useState("从已审核的 Resume Revision 开始渲染。");

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
      });
      setRun(rendered);
      setReport(await getAtsReport(rendered.render_run_id));
      setMessage("生成完成；输出仍是不可变 Artifact，需人工审核后用于申请。");
    } catch (error) {
      setMessage("渲染失败：" + (error as Error).message);
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
      </div>
      <div className="button-row">
        <button className="button button-secondary" type="button" onClick={saveProfile} disabled={!resumeId || !profileId || !title}>保存目标岗位</button>
        <button className="button button-primary" type="button" onClick={render} disabled={!revisionId}>生成预览与 PDF</button>
      </div>
      <p className="resume-studio-message">{message}</p>
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
        </div>
      )}
    </section>
  );
}
