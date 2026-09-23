import { useEffect, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import {
  BarChart3,
  Boxes,
  FileCheck2,
  RefreshCw,
  Target,
  UserRound,
} from "lucide-react";

import type {
  CapabilityNode,
  CapabilityProjection,
  CapabilityRelation,
  PersonalCapabilityState,
} from "../api/capabilities";
import { listCapabilityIdentities } from "../api/capabilities";
import { useCapabilities, type CapabilityQuery } from "../api/useCapabilities";
import { authorityLabels, displayLabel } from "../app/displayLabels";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState, ErrorState, LoadingState } from "../components/ui/States";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { InlineNotice } from "../components/ui/Notice";

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
const relationLabels: Record<string, string> = {
  prerequisite: "前置能力",
  related_to: "相关能力",
  part_of: "组成能力",
  related: "相关能力",
  composition: "组成能力",
  successor: "后继能力",
};

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
        <span className="eyebrow">{layerLabels[node.layer]}</span>
        <h2 id="capability-detail-title">{node.canonical_name}</h2>
        <p>{node.description}</p>
      </header>

      <div className="capability-detail-grid">
        <DetailSection icon={<UserRound size={15} aria-hidden="true" />} title="个人状态">
          {state === null ? <p className="capability-muted">该候选人暂无个人覆盖层。</p> : (
            <>
              <strong className={`badge badge--green capability-status--${state.display_status}`}>
                {statusLabels[state.display_status]}
              </strong>
              <dl className="capability-dimensions">
                <div><dt>理解</dt><dd>{state.understand ? "是" : "否"}</dd></div>
                <div><dt>讲解</dt><dd>{state.explain ? "是" : "否"}</dd></div>
                <div><dt>应用</dt><dd>{state.apply ? "是" : "否"}</dd></div>
                <div><dt>证据</dt><dd>{state.evidence ? "是" : "否"}</dd></div>
                <div><dt>面试</dt><dd>{state.interview_ready ? "就绪" : "未就绪"}</dd></div>
              </dl>
              <small className="text-aux">个人覆盖层 · 第 {state.revision} 版</small>
            </>
          )}
        </DetailSection>

        <DetailSection icon={<FileCheck2 size={15} aria-hidden="true" />} title="证据绑定">
          {projection.evidence_bindings.length === 0 ? <p className="capability-muted">当前状态修订没有证据绑定。</p> : (
            <ul>{projection.evidence_bindings.map((binding) => (
              <li key={binding.binding_id}>
                <strong>{displayLabel(binding.authority, authorityLabels)}</strong>
                <span>{binding.scopes.join(" · ")}</span>
                <code>{binding.binding_id}</code>
              </li>
            ))}</ul>
          )}
        </DetailSection>

        <DetailSection icon={<Target size={15} aria-hidden="true" />} title="目标市场绑定">
          <strong className="capability-count">{projection.target_market_bindings.length}</strong>
          <p>条职业核心返回的目标市场绑定记录</p>
          {projection.target_market_bindings.map((binding) => <code key={binding.binding_id}>{binding.binding_id}</code>)}
        </DetailSection>

        <DetailSection icon={<BarChart3 size={15} aria-hidden="true" />} title="广泛市场绑定">
          <strong className="capability-count">{projection.broad_market_bindings.length}</strong>
          <p>条职业核心返回的广泛市场绑定记录，仅作探索信号</p>
          {projection.broad_market_bindings.map((binding) => <code key={binding.binding_id}>{binding.binding_id}</code>)}
        </DetailSection>

        <DetailSection icon={<Boxes size={15} aria-hidden="true" />} title="投资建议">
          {projection.investment_state === null ? <p className="capability-muted">暂无投资建议。</p> : (
            <>
              <strong className={`investment-label investment-label--${projection.investment_state.recommendation}`}>
                建议 {recommendationLabels[projection.investment_state.recommendation]}
              </strong>
              <p>系统评分 {projection.investment_state.score}</p>
              <ul>{projection.investment_state.reasons.map((reason) => <li key={reason}>{reason}</li>)}</ul>
              <small>这是提案，不是用户优先级。</small>
            </>
          )}
        </DetailSection>

        <DetailSection icon={<Boxes size={15} aria-hidden="true" />} title="图谱关系">
          {relations.length === 0 ? <p className="capability-muted">该节点没有关系记录。</p> : (
            <ul>{relations.map((relation) => (
              <li key={relation.relation_id}>
                <strong>{displayLabel(relation.relation_type, relationLabels)}</strong>
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
  const [identities, setIdentities] = useState<string[]>([]);
  const [identityError, setIdentityError] = useState("");
  const [query, setQuery] = useState<CapabilityQuery | null>(restored ?? null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [state, retry] = useCapabilities(query);

  useEffect(() => {
    const controller = new AbortController();
    listCapabilityIdentities(controller.signal).then((items) => {
      if (controller.signal.aborted) return;
      setIdentities(items);
      if (!restored && items[0]) setQuery({ candidateId: items[0] });
    }).catch(() => {
      if (!controller.signal.aborted) setIdentityError("个人能力档案暂时无法读取。");
    });
    return () => controller.abort();
  }, [restored]);

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

  return (
    <main className="page page--wide">
      <PageHeader
        eyebrow="能力工作台"
        title="能力地图"
        description="查看官方图谱、个人覆盖、市场信号与投资提案。"
        actions={
          <>
            <Field label="个人能力档案" className="capability-header-field">
              <select
                className="select"
                aria-label="选择个人能力档案"
                value={query?.candidateId ?? ""}
                onChange={(event) => setQuery({ candidateId: event.target.value })}
              >
                <option value="">请选择</option>
                {identities.map((identity, index) => <option key={identity} value={identity}>我的能力档案 {index + 1}</option>)}
              </select>
            </Field>
            <Button variant="secondary" onClick={retry} disabled={!query} icon={<RefreshCw size={14} aria-hidden="true" />}>刷新能力地图</Button>
            <Link className="btn btn--quiet" to="/capabilities/inbox" state={{ capabilityQuery: query }}>审核能力候选</Link>
          </>
        }
      />

      <Surface>
        {identityError && (
          <div className="section" style={{ paddingBottom: 0 }}>
            <InlineNotice tone="danger" role="alert">{identityError}</InlineNotice>
          </div>
        )}
        <div className="section">
          {state.status === "idle" && (
            <EmptyState
              icon={UserRound}
              title="还没有个人能力档案"
              description="先确认一条个人能力状态；系统不会猜测或混合不同身份的数据。"
            />
          )}
          {state.status === "loading" && <LoadingState label="正在加载能力地图…" />}
          {state.status === "error" && (
            <ErrorState
              title="能力地图不可用"
              description="恢复连接后重试即可。"
              detail={state.message}
              onRetry={retry}
            />
          )}
          {state.status === "ready" && state.data.graph_version === null && (
            <EmptyState
              icon={Boxes}
              title="暂无官方能力图谱"
              description="职业核心返回了空能力工作台，没有生成示例数据。"
            />
          )}

          {state.status === "ready" && state.data.graph_version !== null && (
            <>
              <div className="metrics-strip capability-metrics" aria-label="能力数字">
                <div>
                  <span>节点数</span>
                  <strong>{state.data.nodes.length}</strong>
                </div>
                <div>
                  <span>目标市场信号</span>
                  <strong>{state.data.projections.reduce((sum, item) => sum + item.target_market_bindings.length, 0)}</strong>
                </div>
                <div>
                  <span>广泛市场信号</span>
                  <strong>{state.data.projections.reduce((sum, item) => sum + item.broad_market_bindings.length, 0)}</strong>
                </div>
                <div>
                  <span>图谱版本</span>
                  <strong>{state.data.graph_version.version_label}</strong>
                </div>
              </div>
              <div className="capability-workspace-layout" style={{ marginTop: "var(--space-5)" }}>
                <section className="capability-node-panel" aria-labelledby="capability-node-title">
                  <header>
                    <div>
                      <h2 id="capability-node-title">官方节点</h2>
                      <p>个人覆盖 · {state.data.nodes.length} 个节点</p>
                    </div>
                    <span>{state.data.input_revisions.length} 个输入引用</span>
                  </header>
                  {state.data.nodes.length === 0 ? <div className="capability-node-empty text-aux">该图谱版本没有节点。</div> : (
                    <div className="capability-node-list">
                      {state.data.nodes.map((node, index) => {
                        const projection = state.data.projections[index];
                        return (
                          <button key={node.capability_id} type="button" aria-pressed={selectedIndex === index} onClick={() => setSelectedIndex(index)}>
                            <span className={`capability-node-mark capability-node-mark--${node.layer}`} />
                            <span><strong>{node.canonical_name}</strong><small>{layerLabels[node.layer]}</small></span>
                            <span className="capability-node-signals"><small>目标市场 {projection.target_market_bindings.length}</small><small>广泛市场 {projection.broad_market_bindings.length}</small>{projection.personal_state && <em>{statusLabels[projection.personal_state.display_status]}</em>}</span>
                          </button>
                        );
                      })}
                    </div>
                  )}
                </section>
                {selected && <CapabilityDetail node={selected.node} projection={selected.projection} relations={selected.relations} />}
              </div>
            </>
          )}
        </div>
      </Surface>
    </main>
  );
}
