import { ExternalLink, Globe2, Search } from "lucide-react";
import { useState } from "react";

import { localizedApiError } from "../api/client";
import {
  admitStagedJob,
  listJobRequirements,
  proposeJobRequirement,
  reviewJobRequirement,
  type JobRequirement,
  searchOfficialJobs,
  type JobStagingRecord,
  type OfficialSourceSearchRequest,
} from "../api/jobRadar";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { Section, Surface } from "../components/ui/Section";
import { InlineNotice } from "../components/ui/Notice";

const sourceLabels: Record<OfficialSourceSearchRequest["source_id"], string> = {
  "official-cn-tencent-campus": "腾讯校招",
  "official-cn-meitu-campus": "美图校招",
};

async function digest(value: string): Promise<string> {
  const bytes = new TextEncoder().encode(value);
  const hash = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(hash)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

export function OfficialSourcesPanel() {
  const [sourceId, setSourceId] = useState<OfficialSourceSearchRequest["source_id"]>("official-cn-tencent-campus");
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<JobStagingRecord[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [requirements, setRequirements] = useState<Record<string, JobRequirement[]>>({});
  const [busy, setBusy] = useState<string | null>(null);

  async function search() {
    setLoading(true);
    setMessage("");
    try {
      const next = await searchOfficialJobs({ source_id: sourceId, query: query.trim() });
      setItems(next);
      setMessage(next.length > 0 ? `已读取 ${next.length} 条官方岗位，均需你逐条确认。` : "官方页面暂未返回可解析岗位；这不代表来源失效。请稍后手动重试。 ");
    } catch (error) {
      setMessage(localizedApiError(error));
    } finally {
      setLoading(false);
    }
  }

  async function admitAndPrepare(item: JobStagingRecord) {
    setBusy(item.staging_id);
    setMessage("");
    try {
      const admission = await admitStagedJob(item.staging_id) as { admission?: { decision?: { job?: { job_id: string; revision: number } } } };
      const job = admission.admission?.decision?.job;
      if (!job) throw new Error("岗位纳入结果缺少岗位版本");
      const evidence = `evidence_job_staging_${await digest(`${item.staging_id}${item.raw_sha256}`)}`;
      const existing = await listJobRequirements(job.job_id, job.revision);
      for (const [index, text] of item.normalized.requirements.entries()) {
        const requirementId = `requirement_${item.staging_id.slice(-12)}_${index + 1}`;
        if (existing.some((requirement) => requirement.requirement_id === requirementId)) continue;
        await proposeJobRequirement(job.job_id, job.revision, {
          requirement_id: requirementId,
          requirement_text: text,
          source_evidence_refs: [evidence],
        });
      }
      const nextRequirements = await listJobRequirements(job.job_id, job.revision);
      setRequirements((current) => ({ ...current, [item.staging_id]: nextRequirements }));
      setItems((current) => current.map((row) => row.staging_id === item.staging_id ? { ...row, status: "admitted", admitted_job_id: job.job_id } : row));
      setMessage("岗位已加入求职流程；候选要求已生成，请逐条审核。接受要求前需绑定正式能力。");
    } catch (error) {
      setMessage(localizedApiError(error));
    } finally {
      setBusy(null);
    }
  }

  async function review(item: JobStagingRecord, requirement: JobRequirement, decision: "accepted" | "rejected") {
    setBusy(requirement.requirement_id);
    try {
      const result = await reviewJobRequirement(requirement.requirement_id, requirement.revision, {
        decision,
        review_reason: decision === "accepted" ? "用户确认纳入岗位匹配" : "用户确认不纳入岗位匹配",
      });
      setRequirements((current) => ({ ...current, [item.staging_id]: current[item.staging_id].map((row) => row.requirement_id === requirement.requirement_id ? result.requirement : row) }));
      setMessage(decision === "accepted" ? "接受需要能力映射；请先在能力档案中绑定后重试。" : "候选要求已拒绝并保留审核记录。");
    } catch (error) {
      setMessage(localizedApiError(error));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Surface>
      <Section
        title="国内官方校招来源"
        icon={Globe2}
        description="只读访问企业官方校招页面；结果先进入岗位暂存区，不会自动加入求职流程。"
        meta={`${items.length} 条结果`}
      >
        <div className="control-group">
          <Field label="来源">
            <select className="select" aria-label="官方校招来源" value={sourceId} onChange={(event) => setSourceId(event.target.value as OfficialSourceSearchRequest["source_id"])}>
              {Object.entries(sourceLabels).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
            </select>
          </Field>
          <Field label="关键词">
            <input className="input" aria-label="官方岗位关键词" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="例如：AI、Agent、实习" />
          </Field>
          <Button variant="primary" loading={loading} onClick={() => void search()} icon={<Search size={15} aria-hidden="true" />}>读取官方岗位</Button>
        </div>
        {message && <InlineNotice tone={message.startsWith("已读取") ? "success" : "muted"} role="status">{message}</InlineNotice>}
        {items.length > 0 && <div className="record-list" aria-label="官方岗位结果">
          {items.map((item) => <article className="record-list__item" key={item.staging_id}>
            <div>
              <strong>{item.normalized.title}</strong>
              <p className="text-aux">{item.normalized.company} · {item.normalized.location || "地点未记录"} · {item.status === "admitted" ? "已加入求职流程" : "待选择"}</p>
              {item.normalized.requirements.length > 0 && <ul>{item.normalized.requirements.map((requirement) => <li key={requirement}>{requirement}</li>)}</ul>}
              <small>来源快照 SHA-256：{item.raw_sha256.slice(0, 12)}…</small>
            </div>
            {item.status === "staged" && <Button size="sm" variant="primary" loading={busy === item.staging_id} onClick={() => void admitAndPrepare(item)}>加入并审核 JD</Button>}
            {item.status === "admitted" && <div className="record-list__requirements" aria-label={`${item.normalized.title} JD 候选要求`}>
              {(requirements[item.staging_id] ?? []).map((requirement) => <div key={requirement.requirement_id}>
                <span>{requirement.requirement_text} · {requirement.status}</span>
                {requirement.status === "proposed" && <span className="button-row"><Button size="sm" variant="secondary" loading={busy === requirement.requirement_id} onClick={() => void review(item, requirement, "rejected")}>拒绝</Button><Button size="sm" variant="primary" loading={busy === requirement.requirement_id} onClick={() => void review(item, requirement, "accepted")}>接受</Button></span>}
                {requirement.review_reason && <small>{requirement.review_reason}</small>}
              </div>)}
            </div>}
            {item.normalized.source_url && <a href={item.normalized.source_url} target="_blank" rel="noreferrer" aria-label={`打开 ${item.normalized.title} 官方来源`}><ExternalLink size={16} aria-hidden="true" /></a>}
          </article>)}
        </div>}
      </Section>
    </Surface>
  );
}
