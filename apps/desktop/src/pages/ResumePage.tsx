import { getResumeBase, getResumeRevision } from "../api/projectResume";
import { RecordLookup, StructuredSections } from "./RecordLookup";
import { ResumeStudioPanel } from "./ResumeStudioPanel";
const loadRevision = (id: string, _revision: string, signal: AbortSignal) => getResumeRevision(id, signal);
export function ResumePage() {
  return <main className="page record-page"><header className="page-heading"><div><p className="eyebrow">Resume</p><h1>简历记录</h1><p>分别读取基础内容与已生成的不可变修订。本页仅供查看，未提供编辑、审核或 PDF 导出。</p></div></header>
    <RecordLookup label="Resume Base" revision load={getResumeBase}>{(base) => <>
      <h2>基础内容 Base</h2><p>{base.resume_id}#{base.revision}</p><p>候选人：{base.candidate_id}</p><p>记录者：{base.created_by} · {base.created_at}</p><StructuredSections value={base.sections} />
    </>}</RecordLookup>
    <RecordLookup label="Resume Revision" load={loadRevision}>{(item) => <>
      <h2>不可变修订 Revision</h2><p>{item.revision_id}</p><p>来源 Base：{item.resume_id}#{item.base_revision}</p><p>SHA-256：{item.content_sha256}</p><p>记录者：{item.created_by} · {item.created_at}</p><h3>已接受 Patch 精确引用</h3>{item.accepted_patch_refs.length ? <ul>{item.accepted_patch_refs.map((ref) => <li key={`${ref.entity_id}:${ref.revision}`}>{ref.entity_id}#{ref.revision}</li>)}</ul> : <p>无 Patch 引用。</p>}<StructuredSections value={item.content} />
    </>}</RecordLookup>
    <ResumeStudioPanel />
  </main>;
}
