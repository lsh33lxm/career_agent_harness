import { Brain, Check, FileText, History, MessageSquarePlus, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { listApplications, type ApplicationRead } from "../api/history";
import { listMemories, type MemorySearchResult } from "../api/memory";
import { listOpportunities, type OpportunitySummary } from "../api/client";
import { listResumeBases, type ResumeBaseRead } from "../api/projectResume";
import { createCommunicationDraft } from "../api/communications";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { InlineNotice, ErrorNotice } from "../components/ui/Notice";

function id(prefix: string): string {
  return `${prefix}_${globalThis.crypto.randomUUID?.().replaceAll("-", "_") ?? Date.now()}`;
}

export function AIWorkbenchPage() {
  const [opportunities, setOpportunities] = useState<OpportunitySummary[]>([]);
  const [resumes, setResumes] = useState<ResumeBaseRead[]>([]);
  const [applications, setApplications] = useState<ApplicationRead[]>([]);
  const [memories, setMemories] = useState<MemorySearchResult[]>([]);
  const [opportunityId, setOpportunityId] = useState("");
  const [resumeId, setResumeId] = useState("");
  const [applicationId, setApplicationId] = useState("");
  const [prompt, setPrompt] = useState("");
  const [draft, setDraft] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      listOpportunities(controller.signal), listResumeBases(controller.signal),
      listApplications(controller.signal), listMemories(controller.signal),
    ]).then(([opportunityItems, resumeItems, applicationItems, memoryItems]) => {
      setOpportunities(opportunityItems);
      setResumes(resumeItems);
      setApplications(applicationItems);
      setMemories(memoryItems);
      setOpportunityId(opportunityItems[0]?.opportunity.entity_id ?? "");
      setResumeId(resumeItems[0]?.resume_id ?? "");
      setApplicationId(applicationItems[0]?.entity_id ?? "");
    }).catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "上下文暂不可用"));
    return () => controller.abort();
  }, []);

  const selectedApplication = applications.find((item) => item.entity_id === applicationId);
  const selectedOpportunity = opportunities.find((item) => item.opportunity.entity_id === opportunityId);
  const selectedResume = resumes.find((item) => item.resume_id === resumeId);
  const contextSummary = useMemo(() => [
    selectedOpportunity ? `岗位 ${selectedOpportunity.opportunity.entity_id}` : "未绑定岗位",
    selectedResume ? `简历 ${selectedResume.resume_id} v${selectedResume.revision}` : "未绑定简历",
    selectedApplication ? `Application ${selectedApplication.entity_id} (${selectedApplication.state})` : "未绑定 Application",
    `已确认记忆 ${memories.length} 条`,
  ].join(" · "), [memories.length, selectedApplication, selectedOpportunity, selectedResume]);

  function generate() {
    const title = selectedOpportunity ? "基于已选岗位生成的准备建议" : "通用求职准备建议";
    setDraft(`${title}\n\n${prompt.trim() || "请根据绑定的岗位、简历、Application 和已确认记忆，列出三个下一步准备动作。"}\n\n依据：${contextSummary}\n\n边界：这是待确认草稿，不会修改基础简历、Application 或发送任何消息。`);
    setMessage("");
  }

  async function saveDraft() {
    if (!draft.trim() || !opportunityId) return;
    try {
      await createCommunicationDraft({
        draft_id: id("ai_draft"), opportunity_id: opportunityId,
        channel: "follow_up_note", body: draft.trim(),
        provenance: {
          source: "ai_workbench", opportunity_id: opportunityId,
          resume_id: resumeId || "unbound", application_id: applicationId || "unbound",
        },
      });
      setMessage("建议已保存到待确认草稿队列，不会自动发送。");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "保存草稿失败");
    }
  }

  return (
    <main className="page page--wide">
      <PageHeader eyebrow="上下文感知" title="AI 工作台" description="绑定职业资料，生成可审核的建议和草稿。" actions={<span className="badge badge--green"><ShieldCheck size={13} aria-hidden="true" />写入需确认</span>} />
      {error && <ErrorNotice label="工作台暂不可用" detail={error} />}
      {message && <InlineNotice tone="success" role="status">{message}</InlineNotice>}
      <Surface>
        <Section title="绑定上下文" icon={Brain} description="只读取你选择的资料，稳定 ID 会写入草稿 provenance。">
          <div className="form-grid">
            <Field label="岗位"><select className="select" aria-label="绑定岗位" value={opportunityId} onChange={(event) => setOpportunityId(event.target.value)}><option value="">请选择岗位</option>{opportunities.map((item) => <option key={item.opportunity.entity_id} value={item.opportunity.entity_id}>{item.opportunity.entity_id}</option>)}</select></Field>
            <Field label="基础简历"><select className="select" aria-label="绑定基础简历" value={resumeId} onChange={(event) => setResumeId(event.target.value)}><option value="">不绑定</option>{resumes.map((item) => <option key={item.resume_id} value={item.resume_id}>{item.resume_id} v{item.revision}</option>)}</select></Field>
            <Field label="Application"><select className="select" aria-label="绑定 Application" value={applicationId} onChange={(event) => setApplicationId(event.target.value)}><option value="">不绑定</option>{applications.map((item) => <option key={item.entity_id} value={item.entity_id}>{item.entity_id} · {item.state}</option>)}</select></Field>
          </div>
          <p className="muted">{contextSummary}</p>
        </Section>
        <Section title="生成建议" icon={FileText} description="当前为本地规则草稿；接入模型后仍必须保留待确认队列。">
          <Field label="你的问题"><textarea className="textarea" aria-label="你的问题" value={prompt} onChange={(event) => setPrompt(event.target.value)} placeholder="例如：围绕这个岗位，我下一步应该补哪三项证据？" /></Field>
          <div className="memory-actions"><Button variant="primary" onClick={generate} icon={<Brain size={14} aria-hidden="true" />}>生成建议</Button></div>
          {draft && <div className="proposal-box"><p>{draft}</p><Button size="sm" variant="secondary" onClick={() => void saveDraft()} icon={<MessageSquarePlus size={14} aria-hidden="true" />}>保存到待确认草稿</Button></div>}
        </Section>
        <Section title="安全边界" icon={History}>
          <ul className="check-list"><li><Check size={14} aria-hidden="true" />不会覆盖基础简历或直接改变 Application 状态。</li><li><Check size={14} aria-hidden="true" />沟通内容只进入本地待确认草稿，不自动发信。</li><li><Check size={14} aria-hidden="true" />上下文来源保留岗位、简历、Application 稳定 ID。</li></ul>
        </Section>
      </Surface>
    </main>
  );
}
