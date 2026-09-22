import { FileText, RefreshCw } from "lucide-react";
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
import { restoreResumeRevision } from "../api/resumeStudio";

export function ResumePage() {
  const [bases, setBases] = useState<ResumeBaseRead[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [base, setBase] = useState<ResumeBaseRead | null>(null);
  const [revisions, setRevisions] = useState<ResumeRevisionRead[]>([]);
  const [baseHistory, setBaseHistory] = useState<ResumeBaseRead[]>([]);
  const [selectedRevision, setSelectedRevision] = useState("");
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
        setSelectedRevision(nextRevisions[0]?.revision_id || "");
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

  return (
    <main className="page record-page">
      <header className="page-heading"><div><p className="eyebrow">个人材料</p><h1>简历</h1><p>查看已确认的基础内容和不可变修订；模型建议不会自动成为简历事实。</p></div></header>
      <section className="today-panel record-browser" aria-label="简历浏览器">
        <div className="record-browser__toolbar">
          <label><span>选择简历</span><select aria-label="选择简历" value={selectedId} onChange={(event) => setSelectedId(event.target.value)}><option value="">请选择</option>{bases.map((item, index) => <option key={item.resume_id} value={item.resume_id}>我的简历 {index + 1} · 第 {item.revision} 版</option>)}</select></label>
          <button type="button" onClick={() => setAttempt((value) => value + 1)}><RefreshCw size={15} />刷新</button>
        </div>
        {error && <p className="inline-error" role="alert">{error}</p>}
        {loading && <p role="status">正在读取简历列表…</p>}
        {!loading && bases.length === 0 && <div className="empty-state"><FileText size={24} /><h2>还没有简历记录</h2><p>先在职业事实与证据确认后创建一份基础简历。</p></div>}
        {base && <div className="resume-browser__content">
          <section><h2>基础内容</h2><p>第 {base.revision} 版 · 创建时间：{base.created_at}</p>{baseHistory.length > 1 && <details><summary>查看基础版本历史</summary><ul>{baseHistory.map((item) => <li key={`${item.resume_id}:${item.revision}`}>第 {item.revision} 版 · {item.created_at} · {item.created_by}</li>)}</ul></details>}<StructuredSections value={base.sections} /></section>
          <section><div className="section-heading"><h2>生成修订</h2>{revisions.length > 0 && <label><span className="sr-only">选择生成修订</span><select aria-label="选择生成修订" value={selectedRevision} onChange={(event) => setSelectedRevision(event.target.value)}>{revisions.map((item, index) => <option key={item.revision_id} value={item.revision_id}>修订 {revisions.length - index} · {item.created_at}</option>)}</select></label>}</div>
            {revisions.length === 0 && <p>还没有基于这份简历生成的修订。</p>}
            {revision && <><p>来源基础版本：第 {revision.base_revision} 版</p><button type="button" onClick={restoreSelectedRevision}>恢复为基础简历</button><StructuredSections value={revision.content} /><details><summary>查看精确来源引用</summary><p>内容 SHA-256：{revision.content_sha256}</p>{revision.accepted_patch_refs.length ? <ul>{revision.accepted_patch_refs.map((ref) => <li key={`${ref.entity_id}:${ref.revision}`}>已审核修改 · 第 {ref.revision} 版</li>)}</ul> : <p>无已审核修改引用。</p>}</details></>}
          </section>
        </div>}
      </section>
      <details className="today-panel advanced-tools"><summary>高级修订工具</summary><p>该工具面向精确版本维护，后续将接入可搜索的选择流程。</p><ResumeStudioPanel /></details>
    </main>
  );
}
