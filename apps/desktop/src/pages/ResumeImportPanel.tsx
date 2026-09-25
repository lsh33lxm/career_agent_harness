import { FileUp, ShieldCheck } from "lucide-react";
import { useRef, useState } from "react";

import { importResumeFile, importResumeText, type ResumeValidationResult } from "../api/resumeStudio";
import { saveResumeBase } from "../api/projectResume";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { Section, Surface } from "../components/ui/Section";

function randomId(prefix: string): string {
  return `${prefix}_${crypto.randomUUID().replaceAll("-", "")}`;
}

function readAsBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("文件读取失败"));
    reader.onload = () => {
      const value = String(reader.result ?? "");
      resolve(value.includes(",") ? value.slice(value.indexOf(",") + 1) : value);
    };
    reader.readAsDataURL(file);
  });
}

export function ResumeImportPanel({ onSaved }: { onSaved: () => void }) {
  const fileInput = useRef<HTMLInputElement>(null);
  const [candidateId, setCandidateId] = useState("");
  const [resumeId, setResumeId] = useState("");
  const [result, setResult] = useState<ResumeValidationResult | null>(null);
  const [status, setStatus] = useState("请选择本地简历文件，内容只发送到本机观复服务解析。 ");
  const [busy, setBusy] = useState(false);

  async function parseFile(file: File) {
    setBusy(true);
    setStatus("正在提取简历内容…");
    try {
      const supported = new Set(["text/plain", "text/markdown", "application/pdf"]);
      if (!supported.has(file.type)) throw new Error("当前支持 TXT、Markdown 或 PDF 文件");
      const parsed = await importResumeFile(file.type, await readAsBase64(file));
      setResult(parsed);
      setStatus(parsed.valid ? "已生成待确认预览；确认后才会写入基础简历。" : "解析未通过，请修正文件后重试。");
    } catch (error) {
      setResult(null);
      setStatus(error instanceof Error ? error.message : "简历解析失败");
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    if (!result?.valid || !result.data || !candidateId.trim() || !resumeId.trim()) return;
    setBusy(true);
    try {
      await saveResumeBase({
        command_id: randomId("command_resume_import"),
        resume_id: resumeId.trim(),
        candidate_id: candidateId.trim(),
        sections: result.data,
      }, randomId("resume-import"));
      setStatus("已由用户确认导入基础简历；原有简历记录未被覆盖。 ");
      setResult(null);
      onSaved();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "保存基础简历失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Surface>
      <Section title="导入简历" icon={FileUp} description="先解析并预览提取内容，再由你确认写入新的基础简历版本。">
        <div className="form-grid">
          <Field label="候选人 ID"><input className="input" aria-label="导入候选人 ID" value={candidateId} onChange={(event) => setCandidateId(event.target.value)} placeholder="例如 candidate_001" /></Field>
          <Field label="新简历 ID"><input className="input" aria-label="导入新简历 ID" value={resumeId} onChange={(event) => setResumeId(event.target.value)} placeholder="例如 resume_imported_001" /></Field>
        </div>
        <div className="button-row">
          <input ref={fileInput} type="file" accept=".txt,.md,.markdown,.pdf,text/plain,text/markdown,application/pdf" hidden onChange={(event) => { const file = event.target.files?.[0]; if (file) void parseFile(file); event.currentTarget.value = ""; }} />
          <Button variant="secondary" onClick={() => fileInput.current?.click()} disabled={busy} icon={<FileUp size={14} aria-hidden="true" />}>选择本地文件</Button>
        </div>
        <p className="text-aux" role="status">{status}</p>
        {result?.valid && result.data && (
          <div className="proposal-box">
            <div className="resume-import-preview"><ShieldCheck size={15} aria-hidden="true" /><strong>提取预览</strong><pre>{JSON.stringify(result.data, null, 2)}</pre></div>
            {result.warnings.map((warning) => <p className="text-aux" key={warning}>提示：{warning}</p>)}
            <Button variant="primary" onClick={() => void save()} disabled={busy || !candidateId.trim() || !resumeId.trim()} icon={<ShieldCheck size={14} aria-hidden="true" />}>确认导入基础简历</Button>
          </div>
        )}
        {result && !result.valid && <p role="alert" className="text-aux">{result.errors.join("；") || result.warnings.join("；")}</p>}
      </Section>
    </Surface>
  );
}
