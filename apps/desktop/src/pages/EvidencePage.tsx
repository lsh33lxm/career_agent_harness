import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { LibraryBig } from "lucide-react";
import { ApiError } from "../api/client";
import { getEvidence, listEvidence } from "../api/evidence";
import type { EvidencePageRead, EvidenceProvenance } from "../api/evidence";
import { artifactClassLabels, displayLabel, sourceTypeLabels } from "../app/displayLabels";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { Button } from "../components/ui/Button";
import { StatusBanner } from "../components/ui/Notice";
import "./EvidencePage.css";

type Load<T> = { status: "loading" } | { status: "error"; message: string }
  | { status: "ready"; data: T };
const message = (error: unknown) => error instanceof ApiError && error.status === 404
  ? "这条证据引用不存在。" : "暂时无法读取证据来源，请检查本地 Core 后重试。";
const sourceLabel = (item: EvidenceProvenance) => item.source.source_type === "legacy_historical_unconfirmed"
  ? "历史来源 · 未确认" : displayLabel(item.source.source_type, sourceTypeLabels);
const mediaTypeLabels: Record<string, string> = {
  "text/plain": "纯文本",
  "text/markdown": "Markdown 文档",
  "text/html": "HTML 文档",
  "application/pdf": "PDF 文档",
  "application/json": "JSON 数据",
};

function EvidenceDetail({ refId }: { refId: string }) {
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<Load<EvidenceProvenance>>({ status: "loading" });
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    getEvidence(refId, controller.signal).then((data) => {
      if (!controller.signal.aborted) setState({ status: "ready", data });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ status: "error", message: message(error) });
    });
    return () => controller.abort();
  }, [refId, attempt]);
  const item = state.status === "ready" ? state.data : null;
  return (
    <Surface className="evidence-detail-surface">
      <Section title="来源与快照" ariaLabel="证据详情">
        {state.status === "loading" && <LoadingState compact label="正在读取完整来源链…" />}
        {state.status === "error" && (
          <ErrorState compact title="暂时无法读取证据详情" detail={state.message} onRetry={() => setAttempt((n) => n + 1)} retryLabel="重试详情" />
        )}
        {item && <>
          <p className="evidence-authority">{sourceLabel(item)} · 保存材料不代表确认其中的主张。</p>
          <dl className="dl dl--wide">
            <div><dt>证据引用</dt><dd>{item.evidence_ref.evidence_ref_id}</dd></div>
            <div><dt>来源类型</dt><dd>{displayLabel(item.source.source_type, sourceTypeLabels)}</dd></div>
            <div><dt>来源标识</dt><dd>{item.source.source_id}</dd></div>
            <div><dt>历史位置（仅描述）</dt><dd>{item.source.locator}</dd></div>
            <div><dt>快照</dt><dd>{item.snapshot.snapshot_id}</dd></div>
            <div><dt>采集时间（原始记录）</dt><dd><time>{item.snapshot.captured_at}</time></dd></div>
            <div><dt>制品</dt><dd>{item.artifact.artifact_id}</dd></div>
            <div><dt>SHA-256</dt><dd>{item.artifact.sha256}</dd></div>
            <div><dt>大小</dt><dd>{item.artifact.byte_length.toLocaleString()} 字节</dd></div>
            <div><dt>材料分类</dt><dd>{displayLabel(item.artifact.artifact_class, artifactClassLabels)}</dd></div>
            <div><dt>媒体类型</dt><dd>{mediaTypeLabels[item.artifact.media_type] ?? item.artifact.media_type}</dd></div>
            <div><dt>精确选择器</dt><dd>{item.evidence_ref.selector ?? "未指定"}</dd></div>
          </dl>
        </>}
      </Section>
    </Surface>
  );
}

export function EvidencePage() {
  const [cursor, setCursor] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [state, setState] = useState<Load<EvidencePageRead>>({ status: "loading" });
  const [selected, setSelected] = useState<string | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    setState({ status: "loading" });
    listEvidence(cursor, controller.signal).then((data) => {
      if (!controller.signal.aborted) setState({ status: "ready", data });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ status: "error", message: message(error) });
    });
    return () => controller.abort();
  }, [cursor, attempt]);
  function navigate(next: string | null) { setSelected(null); setCursor(next); }
  return (
    <main className="page">
      <PageHeader
        eyebrow="历史与证据"
        title="证据来源"
        description="回看已保存材料的来源与精确引用。"
        actions={<Link className="btn btn--secondary" to="/history">返回职业历程</Link>}
      />
      <StatusBanner tone="info" title="这里显示当前连接的 Core 记录">
        演练环境与正式环境分别读取，不会自动合并。证据保存不等于事实确认，也不代表个人能力已掌握。
      </StatusBanner>
      <div style={{ marginTop: "var(--space-5)" }}>
        <Surface>
          <Section title="证据列表" ariaLabel="证据列表" meta={state.status === "ready" ? `本页 ${state.data.items.length} 条记录` : undefined}>
            {state.status === "loading" && <LoadingState label="正在读取证据记录…" />}
            {state.status === "error" && (
              <ErrorState title="暂时无法读取证据列表" detail={state.message} onRetry={() => setAttempt((n) => n + 1)} retryLabel="重试列表" />
            )}
            {state.status === "ready" && state.data.items.length === 0 && (
              <EmptyState
                compact
                icon={LibraryBig}
                title={cursor === null ? "还没有证据记录。" : "此页没有更多证据记录。"}
              />
            )}
            {state.status === "ready" && state.data.items.length > 0 && (
              <div className="evidence-items">
                {state.data.items.map((item) => (
                  <button
                    className="evidence-item"
                    type="button"
                    key={item.evidence_ref.evidence_ref_id}
                    aria-pressed={selected === item.evidence_ref.evidence_ref_id}
                    onClick={() => setSelected(item.evidence_ref.evidence_ref_id)}
                  >
                    <strong>{sourceLabel(item)}</strong>
                    <span>{item.evidence_ref.evidence_ref_id}</span>
                    <small>{displayLabel(item.artifact.artifact_class, artifactClassLabels)} · {item.artifact.byte_length.toLocaleString()} 字节</small>
                  </button>
                ))}
              </div>
            )}
            {state.status === "ready" && (
              <div className="evidence-pagination">
                {cursor !== null && <Button variant="secondary" onClick={() => navigate(null)}>返回首页</Button>}
                {state.data.next_cursor !== null
                  ? <Button variant="secondary" onClick={() => navigate(state.data.next_cursor)}>下一页</Button>
                  : <p className="text-aux">已到当前记录末尾。</p>}
              </div>
            )}
          </Section>
        </Surface>
      </div>
      {selected && <div style={{ marginTop: "var(--space-5)" }}><EvidenceDetail key={selected} refId={selected} /></div>}
    </main>
  );
}
