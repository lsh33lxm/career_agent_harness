import { type FormEvent, useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  AlertCircle,
  BarChart3,
  Boxes,
  FileCheck2,
  RefreshCw,
  Search,
  Target,
  UserRound,
} from "lucide-react";

import type {
  CapabilityNode,
  CapabilityProjection,
  CapabilityRelation,
  PersonalCapabilityState,
} from "../api/capabilities";
import { useCapabilities, type CapabilityQuery } from "../api/useCapabilities";

const layerLabels = {
  common_core: "通用核心",
  track: "方向能力",
  opportunity_specific: "机会专项",
} as const;

const statusLabels: Record<PersonalCapabilityState["display_status"], string> = {
  unknown: "未知",
  understood: "已理解",
  practiced: "可讲解",
  applied: "已实践",
  verified: "有验证",
  resume_ready: "简历就绪",
};

const recommendationLabels = { low: "低", medium: "中", high: "高" } as const;

function DetailSection({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="capability-detail-section">
      <h3>{icon}{title}</h3>
      {children}
    </section>
  );
}

function CapabilityDetail({
  node,
  projection,
  relations,
}: {
  node: CapabilityNode;
  projection: CapabilityProjection;
  relations: CapabilityRelation[];
}) {
  const state = projection.personal_state;
  return (
    <article className="capability-detail" aria-labelledby="capability-detail-title">
      <header>
        <span>{layerLabels[node.layer]}</span>
        <h2 id="capability-detail-title">{node.canonical_name}</h2>
        <p>{node.description}</p>
        <code>{node.capability_id}</code>
      </header>

      <div className="capability-detail-grid">
        <DetailSection icon={<UserRound size={17} />} title="个人状态">
          {state === null ? <p className="capability-muted">该候选人暂无个人覆盖层。</p> : (
            <>
              <strong className={`capability-status capability-status--${state.display_status}`}>
                {statusLabels[state.display_status]}
              </strong>
              <dl className="capability-dimensions">
                <div><dt>理解</dt><dd>{state.understand ? "是" : "否"}</dd></div>
                <div><dt>讲解</dt><dd>{state.explain ? "是" : "否"}</dd></div>
                <div><dt>应用</dt><dd>{state.apply ? "是" : "否"}</dd></div>
                <div><dt>证据</dt><dd>{state.evidence ? "是" : "否"}</dd></div>
                <div><dt>面试</dt><dd>{state.interview_ready ? "就绪" : "未就绪"}</dd></div>
              </dl>
              <small>{state.personal_state_id} · revision {state.revision}</small>
            </>
          )}
        </DetailSection>

        <DetailSection icon={<FileCheck2 size={17} />} title="证据绑定">
          {projection.evidence_bindings.length === 0 ? <p className="capability-muted">当前状态修订没有证据绑定。</p> : (
            <ul>{projection.evidence_bindings.map((binding) => (
              <li key={binding.binding_id}>
                <strong>{binding.authority}</strong>
                <span>{binding.scopes.join(" · ")}</span>
                <code>{binding.binding_id}</code>
              </li>
            ))}</ul>
          )}
        </DetailSection>

        <DetailSection icon={<Target size={17} />} title="目标市场绑定">
          <strong className="capability-count">{projection.target_market_bindings.length}</strong>
          <p>条 Core 返回的 TARGET 绑定记录</p>
          {projection.target_market_bindings.map((binding) => <code key={binding.binding_id}>{binding.binding_id}</code>)}
        </DetailSection>

        <DetailSection icon={<BarChart3 size={17} />} title="广泛市场绑定">
          <strong className="capability-count">{projection.broad_market_bindings.length}</strong>
          <p>条 Core 返回的 BROAD 绑定记录，仅作探索信号</p>
          {projection.broad_market_bindings.map((binding) => <code key={binding.binding_id}>{binding.binding_id}</code>)}
        </DetailSection>

        <DetailSection icon={<Boxes size={17} />} title="投资建议">
          {projection.investment_state === null ? <p className="capability-muted">暂无投资建议。</p> : (
            <>
              <strong className={`investment-label investment-label--${projection.investment_state.recommendation}`}>
                建议 {recommendationLabels[projection.investment_state.recommendation]}
              </strong>
              <p>Core score {projection.investment_state.score}</p>
              <ul>{projection.investment_state.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
              <small>这是提案，不是用户优先级。</small>
            </>
          )}
        </DetailSection>

        <DetailSection icon={<Boxes size={17} />} title="图谱关系">
          {relations.length === 0 ? <p className="capability-muted">该节点没有关系记录。</p> : (
            <ul>{relations.map((relation) => (
              <li key={relation.relation_id}>
                <strong>{relation.relation_type}</strong>
                <span>{relation.source_capability_id} → {relation.target_capability_id}</span>
                <code>{relation.relation_id}</code>
              </li>
            ))}</ul>
          )}
        </DetailSection>
      </div>
    </article>
  );
}

export function CapabilitiesPage() {
  const location = useLocation();
  const restored = (location.state as { capabilityQuery?: CapabilityQuery } | null)?.capabilityQuery;
  const [candidateInput, setCandidateInput] = useState(restored?.candidateId ?? "");
  const [graphInput, setGraphInput] = useState(restored?.graphVersionId ?? "");
  const [query, setQuery] = useState<CapabilityQuery | null>(restored ?? null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [state, retry] = useCapabilities(query);

  useEffect(() => setSelectedIndex(0), [state.status === "ready" ? state.data : null]);

  const selected = useMemo(() => {
    if (state.status !== "ready" || state.data.graph_version === null) return null;
    const node = state.data.nodes[selectedIndex];
    const projection = state.data.projections[selectedIndex];
    const relations = state.data.relations.filter(
      (relation) => relation.source_capability_id === node?.capability_id
        || relation.target_capability_id === node?.capability_id,
    );
    return node && projection ? { node, projection, relations } : null;
  }, [selectedIndex, state]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const candidateId = candidateInput.trim();
    if (!candidateId) return;
    const graphVersionId = graphInput.trim();
    setQuery({ candidateId, ...(graphVersionId ? { graphVersionId } : {}) });
  }

  return (
    <main className="capability-page">
      <header className="capability-heading">
        <div><span>Capability Workspace</span><h1>能力地图</h1><p>查看官方图谱、个人覆盖、市场信号与投资提案。</p><Link to="/capabilities/inbox" state={{ capabilityQuery: query }}>审核能力候选</Link></div>
        {state.status === "ready" && state.data.graph_version !== null && (
          <div className="capability-version"><span>Graph</span><strong>{state.data.graph_version.version_label}</strong><code>{state.data.graph_version.graph_version_id}</code></div>
        )}
      </header>

      <form className="capability-query" onSubmit={submit}>
        <label><span>候选人 ID</span><input required value={candidateInput} onChange={(event) => setCandidateInput(event.target.value)} placeholder="candidate_001" /></label>
        <label><span>图谱版本 ID <small>可选</small></span><input value={graphInput} onChange={(event) => setGraphInput(event.target.value)} placeholder="留空使用最新版本" /></label>
        <button type="submit"><Search size={16} />加载能力地图</button>
      </form>

      {state.status === "idle" && <section className="capability-state"><UserRound size={28} /><h2>请选择候选人</h2><p>身份必须显式输入，系统不会猜测或混合个人能力数据。</p></section>}
      {state.status === "loading" && <section className="capability-state" aria-label="能力地图加载中"><span className="status-spinner" /><p>正在加载能力地图…</p></section>}
      {state.status === "error" && <section className="capability-state" role="alert"><AlertCircle size={28} /><h2>能力地图不可用</h2><p>{state.message}</p><button type="button" onClick={retry}><RefreshCw size={15} />重试</button></section>}
      {state.status === "ready" && state.data.graph_version === null && <section className="capability-state"><Boxes size={28} /><h2>暂无官方能力图谱</h2><p>Core 返回了空 workspace，没有生成示例数据。</p></section>}

      {state.status === "ready" && state.data.graph_version !== null && (
        <div className="capability-workspace-layout">
          <section className="capability-node-panel" aria-labelledby="capability-node-title">
            <header><div><h2 id="capability-node-title">官方节点</h2><p>{state.data.candidate_id} · {state.data.nodes.length} 个节点</p></div><span>{state.data.input_revisions.length} 个输入引用</span></header>
            {state.data.nodes.length === 0 ? <div className="capability-node-empty">该图谱版本没有节点。</div> : (
              <div className="capability-node-list">
                {state.data.nodes.map((node, index) => {
                  const projection = state.data.projections[index];
                  return (
                    <button key={node.capability_id} type="button" aria-pressed={selectedIndex === index} onClick={() => setSelectedIndex(index)}>
                      <span className={`capability-node-mark capability-node-mark--${node.layer}`} />
                      <span><strong>{node.canonical_name}</strong><small>{layerLabels[node.layer]}</small></span>
                      <span className="capability-node-signals"><small>T {projection.target_market_bindings.length}</small><small>B {projection.broad_market_bindings.length}</small>{projection.personal_state && <em>{statusLabels[projection.personal_state.display_status]}</em>}</span>
                    </button>
                  );
                })}
              </div>
            )}
          </section>
          {selected && <CapabilityDetail node={selected.node} projection={selected.projection} relations={selected.relations} />}
        </div>
      )}
    </main>
  );
}
