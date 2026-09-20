import { getProject } from "../api/projectResume";
import { RecordLookup } from "./RecordLookup";
export function ProjectsPage() {
  return <main className="page record-page"><header className="page-heading"><div><p className="eyebrow">Projects</p><h1>项目与证据</h1><p>读取已登记项目；项目存在不等于个人掌握。</p></div></header>
    <RecordLookup label="项目" revision load={getProject}>{({ project, evidence }) => <>
      <h2>{project.display_name}</h2><p>{project.project_id}#{project.revision}</p><p>记录者：{project.created_by} · {project.created_at}</p>
      <h3>项目证据的最新修订</h3><p>以下证据独立版本化，不代表所选项目修订当时的历史快照。</p>
      {evidence.length === 0 && <p>此项目尚无已记录证据。</p>}
      {evidence.map((item) => <article key={item.evidence_id}><h3>{item.summary}</h3><p>{item.evidence_id}#{item.revision}</p><p>来源权威：{item.authority} · 复核：{item.review_status} · 时效：{item.freshness}</p><p>Manifest：{item.source_manifest.manifest_id}</p><p>扫描范围引用：{item.source_manifest.scan_scope_id}#{item.source_manifest.scan_scope_revision}</p><ul>{item.source_manifest.entries.map((entry) => <li key={entry.relative_path}>{entry.relative_path}<br />SHA-256：{entry.sha256}<br />{entry.byte_length} bytes</li>)}</ul></article>)}
    </>}</RecordLookup>
  </main>;
}
