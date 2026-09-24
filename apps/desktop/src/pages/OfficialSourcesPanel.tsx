import { ExternalLink, Globe2, Search } from "lucide-react";
import { useState } from "react";

import { localizedApiError } from "../api/client";
import { searchOfficialJobs, type JobStagingRecord, type OfficialSourceSearchRequest } from "../api/jobRadar";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { Section, Surface } from "../components/ui/Section";
import { InlineNotice } from "../components/ui/Notice";

const sourceLabels: Record<OfficialSourceSearchRequest["source_id"], string> = {
  "official-cn-tencent-campus": "腾讯校招",
  "official-cn-meitu-campus": "美图校招",
};

export function OfficialSourcesPanel() {
  const [sourceId, setSourceId] = useState<OfficialSourceSearchRequest["source_id"]>("official-cn-tencent-campus");
  const [query, setQuery] = useState("");
  const [items, setItems] = useState<JobStagingRecord[]>([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

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
              <p className="text-aux">{item.normalized.company} · {item.normalized.location || "地点未记录"} · 待选择</p>
              {item.normalized.requirements.length > 0 && <ul>{item.normalized.requirements.map((requirement) => <li key={requirement}>{requirement}</li>)}</ul>}
              <small>来源快照 SHA-256：{item.raw_sha256.slice(0, 12)}…</small>
            </div>
            {item.normalized.source_url && <a href={item.normalized.source_url} target="_blank" rel="noreferrer" aria-label={`打开 ${item.normalized.title} 官方来源`}><ExternalLink size={16} aria-hidden="true" /></a>}
          </article>)}
        </div>}
      </Section>
    </Surface>
  );
}
