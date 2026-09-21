import { AlertCircle, Check, Inbox, Plus, RefreshCw } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  admitStagedJob,
  importManualJob,
  listJobStaging,
  type JobStagingRecord,
} from "../api/jobRadar";

function message(error: unknown): string {
  return error instanceof Error ? error.message : "职位暂存请求失败";
}

function terms(value: FormDataEntryValue | null): string[] {
  return String(value ?? "").split(",").map((item) => item.trim()).filter(Boolean);
}

export function JobRadarPanel() {
  const [records, setRecords] = useState<JobStagingRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [importing, setImporting] = useState(false);
  const [admitting, setAdmitting] = useState<string | null>(null);

  const load = useCallback(async (signal?: AbortSignal) => {
    setLoading(true);
    setError("");
    try {
      setRecords(await listJobStaging(signal));
    } catch (caught) {
      if (!signal?.aborted) setError(message(caught));
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  async function handleImport(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setImporting(true);
    setError("");
    try {
      await importManualJob({
        source_ref: String(data.get("sourceRef")),
        raw_text: String(data.get("rawText")),
        desired_terms: terms(data.get("desiredTerms")),
        excluded_terms: terms(data.get("excludedTerms")),
      });
      form.reset();
      await load();
    } catch (caught) {
      setError(message(caught));
    } finally {
      setImporting(false);
    }
  }

  async function admit(record: JobStagingRecord) {
    setAdmitting(record.staging_id);
    setError("");
    try {
      await admitStagedJob(record.staging_id);
      await load();
    } catch (caught) {
      setError(message(caught));
    } finally {
      setAdmitting(null);
    }
  }

  return (
    <section className="radar-panel" aria-labelledby="radar-title">
      <div className="section-heading">
        <div>
          <p className="eyebrow">Local staging</p>
          <h2 id="radar-title">Opportunity Radar</h2>
        </div>
        <span>建议排序与用户优先级分离</span>
      </div>
      <form className="radar-import" onSubmit={(event) => void handleImport(event)}>
        <label><span>来源</span><input name="sourceRef" required placeholder="https://… 或 manual://…" /></label>
        <label><span>希望匹配</span><input name="desiredTerms" placeholder="Python, SQLite" /></label>
        <label><span>排除条件</span><input name="excludedTerms" placeholder="On-site" /></label>
        <label className="radar-import__text"><span>职位原文</span><textarea name="rawText" required rows={4} /></label>
        <button className="primary-command" type="submit" disabled={importing}>
          <Plus size={16} aria-hidden="true" />{importing ? "暂存中…" : "导入暂存区"}
        </button>
      </form>
      {error && <p className="inline-error radar-error" role="alert"><AlertCircle size={16} />{error}<button className="secondary-command" type="button" onClick={() => void load()}><RefreshCw size={14} />重试</button></p>}
      {loading && <div className="radar-state" aria-live="polite"><span className="status-spinner" /><p>正在读取暂存职位…</p></div>}
      {!loading && records.length === 0 && <div className="radar-state"><Inbox size={22} /><p>暂存区为空</p></div>}
      {!loading && records.length > 0 && (
        <div className="radar-records">
          {records.map((record) => (
            <article className="radar-record" key={record.staging_id}>
              <div><h3>{record.normalized.title}</h3><p>{record.normalized.company}{record.normalized.location ? ` · ${record.normalized.location}` : ""}</p></div>
              <div className="radar-score"><strong>{Math.round(record.suggested_score * 100)}</strong><span>建议匹配</span></div>
              <div className="radar-notes"><span>{record.status}</span>{record.gaps.length > 0 && <span>缺口：{record.gaps.join("、")}</span>}{record.duplicate_of && <span>重复：{record.duplicate_of}</span>}</div>
              {record.status === "staged" && <button className="secondary-command" type="button" disabled={admitting === record.staging_id} onClick={() => void admit(record)}><Check size={15} />{admitting === record.staging_id ? "纳入中…" : "纳入机会"}</button>}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
