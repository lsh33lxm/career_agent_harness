import { useEffect, useState } from "react";
import type { ReactNode } from "react";
import { ApiError } from "../api/client";
import "./RecordLookup.css";

type Load<T> = { status: "idle" | "loading" } | { status: "error"; message: string } | { status: "ready"; data: T };
export function RecordLookup<T>({ label, revision = false, load, children }: {
  label: string; revision?: boolean; load: (id: string, revision: string, signal: AbortSignal) => Promise<T>;
  children: (data: T) => ReactNode;
}) {
  const [id, setId] = useState(""); const [rev, setRev] = useState("");
  const [request, setRequest] = useState<{ id: string; revision: string; attempt: number } | null>(null);
  const [state, setState] = useState<Load<T>>({ status: "idle" });
  useEffect(() => {
    if (!request) return;
    const controller = new AbortController(); setState({ status: "loading" });
    load(request.id, request.revision, controller.signal).then((data) => {
      if (!controller.signal.aborted) setState({ status: "ready", data });
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setState({ status: "error", message: error instanceof ApiError && error.status === 404 ? "未找到指定记录或修订。" : "读取失败，请检查本地 Core 后重试。" });
    });
    return () => controller.abort();
  }, [request, load]);
  return <section className="today-panel record-lookup">
    <form onSubmit={(event) => { event.preventDefault(); if (id.trim()) setRequest({ id: id.trim(), revision: rev, attempt: (request?.attempt ?? 0) + 1 }); }}>
      <label>{label} ID<input required maxLength={128} value={id} onChange={(event) => setId(event.target.value)} /></label>
      {revision && <label>{label} 修订（留空读取最新）<input type="number" min="1" step="1" value={rev} onChange={(event) => setRev(event.target.value)} /></label>}
      <button type="submit">读取{label}</button>
    </form>
    {state.status === "idle" && <p>输入已知 ID 后读取，不会自动创建或扫描。</p>}
    {state.status === "loading" && <p role="status">正在读取{label}…</p>}
    {state.status === "error" && <div role="alert"><p>{state.message}</p><button type="button" onClick={() => setRequest((old) => old ? { ...old, attempt: old.attempt + 1 } : null)}>重试{label}</button></div>}
    {state.status === "ready" && children(state.data)}
  </section>;
}
export function StructuredSections({ value }: { value: Record<string, unknown> }) {
  return Object.keys(value).length ? <div>{Object.entries(value).map(([key, content]) => <section key={key}><h3>{key}</h3><pre>{JSON.stringify(content, null, 2)}</pre></section>)}</div> : <p>该记录内容为空。</p>;
}
