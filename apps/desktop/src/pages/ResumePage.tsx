import { FileText, Lightbulb, RefreshCw, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import {
  getResumeBase,
  listResumeBases,
  listResumeRevisions,
  listResumeBaseRevisions,
  type ResumeBaseRead,
  type ResumeRevisionRead,
} from "../api/projectResume";
import { StructuredSections } from "./RecordLookup";
import { ResumeStudioPanel } from "./ResumeStudioPanel";
import { getResumeDiff, restoreResumeBaseRevision, restoreResumeRevision, type ResumeStudioDiff } from "../api/resumeStudio";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";

export function ResumePage() {
  const [bases, setBases] = useState<ResumeBaseRead[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [base, setBase] = useState<ResumeBaseRead | null>(null);
  const [revisions, setRevisions] = useState<ResumeRevisionRead[]>([]);
  const [baseHistory, setBaseHistory] = useState<ResumeBaseRead[]>([]);
  const [selectedBaseRevision, setSelectedBaseRevision] = useState("");
  const [selectedRevision, setSelectedRevision] = useState("");
  const [diff, setDiff] = useState<ResumeStudioDiff | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    listResumeBases(controller.signal)
      .then((items) => {
        if (controller.signal.aborted) return;
        setBases(items);
        setSelectedId((current) => current || items[0]?.resume_id || "");
        setLoading(false);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setError("简历列表暂时无法读取，请检查本地服务后重试。");
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [attempt]);

  useEffect(() => {
    if (!selectedId) {
      setBase(null);
      setRevisions([]);
      return;
    }
    const controller = new AbortController();
    Promise.all([
      getResumeBase(selectedId, "", controller.signal),
      listResumeRevisions(selectedId, controller.signal),
      listResumeBaseRevisions(selectedId, controller.signal).catch(() => []),
    ])
      .then(([nextBase, nextRevisions, nextBaseHistory]) => {
        if (controller.signal.aborted) return;
        setBase(nextBase);
        setRevisions(nextRevisions);
        setBaseHistory(nextBaseHistory);
        setSelectedBaseRevision(String(nextBase.revision));
        setSelectedRevision(nextRevisions[0]?.revision_id || "");
        setDiff(null);
      })
      .catch(() => {
        if (!controller.signal.aborted) setError("简历内容暂时无法读取，请选择其他记录或重试。");
      });
    return () => controller.abort();
  }, [selectedId, attempt]);

  const revision = revisions.find((item) => item.revision_id === selectedRevision) ?? null;

  async function restoreSelectedRevision() {
    if (!base || !revision) return;
    setError("");
    try {
      await restoreResumeRevision(
        {
          command_id: `restore_${revision.revision_id}`,
          resume_id: base.resume_id,
          revision_id: revision.revision_id,
          expected_base_revision: base.revision,
        },
        `resume-restore-${revision.revision_id}-${base.revision}`,
      );
      setAttempt((value) => value + 1);
    } catch {
      setError("恢复历史修订失败，请检查当前版本后重试。");
    }
  }

  async function restoreSelectedBase() {
    if (!base || !selectedBaseRevision) return;
    const sourceRevision = Number(selectedBaseRevision);
    if (!Number.isInteger(sourceRevision) || sourceRevision === base.revision) return;
    setError("");
    try {
      await restoreResumeBaseRevision(
        {
          command_id: `base_restore_${base.resume_id}_${sourceRevision}_${base.revision}`,
          resume_id: base.resume_id,
          source_base_revision: sourceRevision,
          expected_base_revision: base.revision,
        },
        `resume-base-restore-${base.resume_id}-${sourceRevision}-${base.revision}`,
      );
      setAttempt((value) => value + 1);
    } catch {
      setError("恢复基础版本失败，请检查当前版本后重试。");
    }
  }

  async function loadSelectedDiff() {
    if (!revision) return;
    setError("");
    try {
      setDiff(await getResumeDiff(revision.revision_id));
    } catch {
      setError("暂时无法读取内容差异，请稍后重试。");
    }
  }

  return (
    <main className="page page--wide">
      <PageHeader
        eyebrow="个人材料"
        title="简历"
        description="查看已确认的基础内容和不可变修订；模型建议不会自动成为简历事实。"
        actions={
          <>
            <Field label="选择简历" className="capability-header-field">
              <select
                className="select"
                aria-label="选择简历"
                value={selectedId}
                onChange={(event) => setSelectedId(event.target.value)}
              >
                <option value="">请选择</option>
                {bases.map((item, index) => (
                  <option key={item.resume_id} value={item.resume_id}>我的简历 {index + 1} · 第 {item.revision} 版</option>
                ))}
              </select>
            </Field>
            <Button variant="secondary" onClick={() => setAttempt((value) => value + 1)} icon={<RefreshCw size={14} aria-hidden="true" />}>刷新</Button>
          </>
        }
      />

      {error && (
        <Surface>
          <Section title="简历档案" icon={FileText} ariaLabel="简历档案">
            <ErrorState compact title="暂时无法读取简历" detail={error} onRetry={() => setAttempt((value) => value + 1)} />
          </Section>
        </Surface>
      )}
      {loading && (
        <Surface>
          <Section title="简历档案" icon={FileText} ariaLabel="简历档案">
            <LoadingState label="正在读取简历列表…" />
          </Section>
        </Surface>
      )}
      {!loading && !error && bases.length === 0 && (
        <Surface>
          <Section title="简历档案" icon={FileText} ariaLabel="简历档案">
            <EmptyState
              icon={FileText}
              title="还没有简历记录"
              description="先在“我的”完成职业事实与证据确认，再创建一份基础简历。"
            />
          </Section>
        </Surface>
      )}

      {base && (
        <div className="resume-workspace">
          <Surface>
            <Section
              title="已确认的职业事实"
              icon={ShieldCheck}
              description="基于你在职业事实与证据中确认的内容生成。"
              meta={`第 ${base.revision} 版 · ${base.created_at}`}
            >
              <StructuredSections value={base.sections} />
              {baseHistory.length > 1 && (
                <details className="disclosure" style={{ marginTop: "var(--space-3)" }}>
                  <summary>查看基础版本历史</summary>
                  <div className="disclosure__body analysis-form">
                    <Field label="选择要恢复的版本">
                      <select
                        className="select"
                        aria-label="选择要恢复的基础版本"
                        value={selectedBaseRevision}
                        onChange={(event) => setSelectedBaseRevision(event.target.value)}
                      >
                        {baseHistory.map((item) => (
                          <option key={`${item.resume_id}:${item.revision}`} value={item.revision}>第 {item.revision} 版 · {item.created_at}</option>
                        ))}
                      </select>
                    </Field>
                    <div>
                      <Button
                        variant="secondary"
                        disabled={Number(selectedBaseRevision) === base.revision}
                        onClick={() => void restoreSelectedBase()}
                      >
                        恢复为新基础版本
                      </Button>
                    </div>
                    <ul className="legacy-interviews">
                      {baseHistory.map((item) => (
                        <li key={`${item.resume_id}:${item.revision}`}>第 {item.revision} 版 · {item.created_at} · {item.created_by}</li>
                      ))}
                    </ul>
                  </div>
                </details>
              )}
            </Section>
          </Surface>

          <Surface>
            <Section
              title="简历预览"
              icon={FileText}
              description="选择左侧内容或先选择简历，开始预览你的简历。"
              meta={revisions.length > 0 ? (
                <select
                  className="select"
                  style={{ maxWidth: "240px" }}
                  aria-label="选择生成修订"
                  value={selectedRevision}
                  onChange={(event) => setSelectedRevision(event.target.value)}
                >
                  {revisions.map((item, index) => (
                    <option key={item.revision_id} value={item.revision_id}>修订 {revisions.length - index} · {item.created_at}</option>
                  ))}
                </select>
              ) : undefined}
            >
              {revisions.length === 0 && <p className="text-aux">还没有基于这份简历生成的修订。</p>}
              {revision && (
                <>
                  <p className="text-aux">来源基础版本：第 {revision.base_revision} 版</p>
                  <div className="resume-actions">
                    <Button size="sm" variant="secondary" onClick={() => void restoreSelectedRevision()}>恢复为基础简历</Button>
                    <Button size="sm" variant="secondary" onClick={() => void loadSelectedDiff()}>查看内容差异</Button>
                  </div>
                  {diff && (
                    <details className="disclosure" open>
                      <summary>内容差异与来源</summary>
                      <div className="disclosure__body">
                        <pre className="resume-diff">{diff.diff}</pre>
                        {diff.claim_provenance.length > 0 && (
                          <p className="text-aux">事实引用：{diff.claim_provenance.map((ref) => `${ref.entity_id} 第 ${ref.revision} 版`).join("、")}</p>
                        )}
                        {diff.evidence_provenance.length > 0 && (
                          <p className="text-aux">证据引用：{diff.evidence_provenance.join("、")}</p>
                        )}
                      </div>
                    </details>
                  )}
                  <StructuredSections value={revision.content} />
                  <details className="disclosure">
                    <summary>查看精确来源引用</summary>
                    <div className="disclosure__body">
                      <p className="text-aux">内容 SHA-256：{revision.content_sha256}</p>
                      {revision.accepted_patch_refs.length ? (
                        <ul className="legacy-interviews">
                          {revision.accepted_patch_refs.map((ref) => <li key={`${ref.entity_id}:${ref.revision}`}>已审核修改 · 第 {ref.revision} 版</li>)}
                        </ul>
                      ) : <p className="text-aux">无已审核修改引用。</p>}
                    </div>
                  </details>
                </>
              )}
              <div className="resume-tip">
                <Lightbulb size={16} aria-hidden="true" />
                <div>
                  <strong>小提示：让简历更出色</strong>
                  <p>从左侧已确认的职业事实生成简历。模型建议仅用于优化表达，不会自动覆盖你的已确认内容。</p>
                </div>
              </div>
            </Section>
          </Surface>
        </div>
      )}

      <details className="disclosure" style={{ marginTop: "var(--space-5)" }}>
        <summary>高级修订工具</summary>
        <div className="disclosure__body">
          <p className="text-aux" style={{ marginBottom: "var(--space-3)" }}>该工具面向精确版本维护，后续将接入可搜索的选择流程。</p>
          <ResumeStudioPanel />
        </div>
      </details>
    </main>
  );
}
