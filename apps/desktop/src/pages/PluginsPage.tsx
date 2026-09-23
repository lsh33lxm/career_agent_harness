import { useCallback, useEffect, useState } from "react";
import { HeartPulse, Monitor, Package, Power, RefreshCw, RotateCcw, ShieldCheck, Undo2, XCircle } from "lucide-react";

import {
  getPluginAuditSummary,
  listPluginAudit,
  previewPluginUninstall,
  setPluginUpdatePolicy,
  type PluginAuditEvent,
  type PluginAuditSummary,
  type PluginCatalogItem,
  type PluginUninstallPreview,
} from "../api/plugins";
import { apiRequest } from "../api/client";
import { useHealth } from "../api/useHealth";
import { ModelProvidersPanel } from "./ModelProvidersPanel";
import { TaskQueuePanel } from "./TaskQueuePanel";
import { PageHeader } from "../components/ui/PageHeader";
import { Section, Surface } from "../components/ui/Section";
import { EmptyState, LoadingState } from "../components/ui/States";
import { Button } from "../components/ui/Button";
import { ErrorNotice, InlineNotice, StatusBanner } from "../components/ui/Notice";

function statusLabel(item: PluginCatalogItem): string {
  if (!item.installed) return "未安装";
  if (item.installation?.enabled) return "已启用";
  return item.installation?.status === "rolled_back" ? "已回滚" : "已停用";
}

const displayLabels: Record<string, string> = {
  builtin_adapter: "内置适配器",
  mcp_plugin: "MCP 工具",
  worker_plugin: "本地工具",
  knowledge_plugin: "知识工具",
  ui_plugin: "界面工具",
  "fixture.echo": "本地连通性检查",
  "knowledge.search": "知识检索",
  "knowledge.read": "读取知识",
  "knowledge.ask": "知识问答",
  "knowledge.list": "浏览知识库",
  "resume.render": "简历渲染",
  health: "健康检查",
  user: "用户",
  system: "系统",
  install: "安装",
  enable: "启用",
  disable: "停用",
  healthcheck: "健康检查",
  rollback: "回滚",
  update_preview: "更新预览",
  passed: "通过",
  verified: "已验证",
  unknown: "未知",
  offline_pass: "离线检查通过",
  offline_review_required: "需要人工复核",
  approved: "已批准",
  pending: "待处理",
  notify: "仅提醒",
  patch_auto: "准备补丁预览",
  manual: "手动批准",
};

const toolCopy: Record<string, { name: string; description: string }> = {
  "career-kb-local": {
    name: "本地职业知识库",
    description: "只读访问本地职业知识；不会改写 Career Core 的权威数据。",
  },
  "career-kb-weknora": {
    name: "WeKnora 职业知识库",
    description: "只读访问 WeKnora；配置服务地址、凭据并确认使用条款后才可启用。",
  },
  "echo-fixture": {
    name: "本地连通性检查",
    description: "用于验证工具协议的确定性离线检查工具。",
  },
};

function toolName(item: PluginCatalogItem): string {
  return toolCopy[item.manifest.id]?.name ?? item.manifest.name;
}

function toolDescription(item: PluginCatalogItem): string {
  return toolCopy[item.manifest.id]?.description ?? item.manifest.user_visible_description;
}

function displayLabel(value: string | null | undefined, fallback = "未记录"): string {
  if (!value) return fallback;
  return displayLabels[value] ?? value.replaceAll("_", " ");
}

export function PluginsPage() {
  const [items, setItems] = useState<PluginCatalogItem[]>([]);
  const [message, setMessage] = useState("正在读取本地工具目录…");
  const [pending, setPending] = useState("");
  const [actionMessage, setActionMessage] = useState("");
  const [actionDetail, setActionDetail] = useState("");
  const [auditPluginId, setAuditPluginId] = useState("");
  const [auditEvents, setAuditEvents] = useState<PluginAuditEvent[]>([]);
  const [auditSummary, setAuditSummary] = useState<PluginAuditSummary | null>(null);
  const [uninstallPreview, setUninstallPreview] = useState<PluginUninstallPreview | null>(null);
  const [tab, setTab] = useState<"models" | "tools" | "tasks">("models");
  const [health, retryHealth] = useHealth();

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      setItems(await apiRequest<PluginCatalogItem[]>("/api/v1/plugins", { signal }));
      setMessage("");
    } catch (error) {
      if (!signal?.aborted) setMessage("本地工具目录暂不可用：" + (error as Error).message);
    }
  }, []);

  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => controller.abort(); }, [load]);

  async function act(item: PluginCatalogItem, action: string) {
    const key = `${item.manifest.id}:${action}`;
    setPending(key);
    setActionMessage("");
    setActionDetail("");
    try {
      const path = action === "install" ? "/api/v1/plugins/install" : `/api/v1/plugins/${encodeURIComponent(item.manifest.id)}/${action}`;
      const body = action === "install" ? JSON.stringify({ manifest: item.manifest }) : action === "update-preview" ? JSON.stringify({ fixture: {} }) : undefined;
      const result = await apiRequest<Record<string, unknown>>(path, { method: "POST", ...(body ? { body } : {}) });
      setActionMessage(`${item.manifest.name}：${action === "update-preview" ? (result.tests as { safe_to_switch?: boolean })?.safe_to_switch ? "更新检查通过" : "更新已隔离" : "操作完成"}`);
      await load();
    } catch (error) {
      setActionMessage(`${item.manifest.name}：操作未完成，请重试。`);
      setActionDetail((error as Error).message);
    } finally {
      setPending("");
    }
  }

  async function showAudit(item: PluginCatalogItem) {
    if (auditPluginId === item.manifest.id) {
      setAuditPluginId("");
      setAuditEvents([]);
      setAuditSummary(null);
      return;
    }
    setPending(`${item.manifest.id}:audit`);
    setActionMessage("");
    setActionDetail("");
    try {
      const [events, summary] = await Promise.all([
        listPluginAudit(item.manifest.id),
        getPluginAuditSummary(item.manifest.id),
      ]);
      setAuditPluginId(item.manifest.id);
      setAuditEvents(events);
      setAuditSummary(summary);
    } catch (error) {
      setActionMessage(`${item.manifest.name}：审计读取失败，请重试。`);
      setActionDetail((error as Error).message);
    } finally {
      setPending("");
    }
  }

  async function showUninstallPreview(item: PluginCatalogItem) {
    setPending(`${item.manifest.id}:uninstall-preview`);
    setActionMessage("");
    setActionDetail("");
    try {
      setUninstallPreview(await previewPluginUninstall(item.manifest.id));
    } catch (error) {
      setActionMessage(`${item.manifest.name}：卸载影响读取失败，请重试。`);
      setActionDetail((error as Error).message);
    } finally {
      setPending("");
    }
  }

  async function changePolicy(item: PluginCatalogItem, policy: "notify" | "patch_auto" | "manual") {
    setPending(`${item.manifest.id}:policy`);
    setActionMessage("");
    setActionDetail("");
    try {
      await setPluginUpdatePolicy(item.manifest.id, policy);
      setActionMessage(`${item.manifest.name}：更新策略已设为 ${displayLabel(policy)}`);
      await load();
    } catch (error) {
      setActionMessage(`${item.manifest.name}：更新策略保存失败，请重试。`);
      setActionDetail((error as Error).message);
    } finally {
      setPending("");
    }
  }

  const loading = message.startsWith("正在读取");

  return (
    <main className="page page--wide">
      <PageHeader
        eyebrow="本地接入"
        title="工具与模型"
        description="管理本地工具的权限、健康状态与更新。模型服务配置将在“模型服务”区域显示。"
        actions={<span className="badge"><Package size={12} aria-hidden="true" />本地目录</span>}
      />

      <Surface>
        <Section
          title="本地服务"
          icon={Monitor}
          meta={<span className={health.status === "online" ? "badge badge--green" : health.status === "offline" ? "badge badge--danger" : "badge"}>{health.status === "online" ? "正常运行" : health.status === "offline" ? "离线" : "连接中"}</span>}
        >
          <div className="service-strip">
            <div className="service-strip__cell">
              <span className="text-aux">服务状态</span>
              <strong>{health.status === "online" ? "本地服务已连接" : health.status === "offline" ? "本地服务离线" : "正在连接"}</strong>
              <p className="text-aux">{health.status === "online" ? "本地工具目录可用，已连接到本地服务。" : "本地服务未响应时，工具与模型配置不可用。"}</p>
            </div>
            <div className="service-strip__cell">
              <span className="text-aux">可用工具</span>
              <strong className="service-strip__num">{items.length}</strong>
            </div>
            <div className="service-strip__cell">
              <span className="text-aux">版本信息</span>
              <strong>{health.status === "online" ? `v${health.data.version}` : "—"}</strong>
            </div>
            <div className="service-strip__actions">
              <Button size="sm" variant="secondary" onClick={retryHealth} icon={<RotateCcw size={13} aria-hidden="true" />}>重试</Button>
            </div>
          </div>
          {health.status === "offline" && (
            <details className="state__details" style={{ marginTop: "var(--space-3)" }}>
              <summary>查看诊断</summary>
              <pre>{health.message}</pre>
            </details>
          )}
        </Section>
      </Surface>

      {actionMessage && (
        <div style={{ marginTop: "var(--space-4)" }}>
          {actionDetail
            ? <ErrorNotice label={actionMessage} detail={actionDetail} />
            : <InlineNotice tone={actionMessage.includes("失败") || actionMessage.includes("隔离") ? "danger" : "success"} role="status">{actionMessage}</InlineNotice>}
        </div>
      )}

      <div className="tab-bar" role="tablist" aria-label="工具与模型分区">
        <button type="button" role="tab" aria-selected={tab === "models"} onClick={() => setTab("models")}>模型服务</button>
        <button type="button" role="tab" aria-selected={tab === "tools"} onClick={() => setTab("tools")}>本地工具</button>
        <button type="button" role="tab" aria-selected={tab === "tasks"} onClick={() => setTab("tasks")}>任务队列</button>
      </div>

      {tab === "models" && (
        <Surface>
          <Section title="模型服务" description="配置和管理大语言模型服务，用于简历优化、面试准备等智能功能。选择厂商预设后只需填入 API Key。">
            <ModelProvidersPanel />
          </Section>
        </Surface>
      )}

      {tab === "tools" && (
        <>
          {loading && <LoadingState compact label={message} />}
          {!loading && message && (
            <div style={{ marginBottom: "var(--space-4)" }}>
              <StatusBanner tone="warning" title="本地工具目录暂不可用">
                本地职业核心未响应，恢复连接后工具目录会自动显示；已安装工具的状态不会丢失。
              </StatusBanner>
              <details className="state__details" style={{ marginTop: "var(--space-2)" }}>
                <summary>查看诊断</summary>
                <pre>{message}</pre>
              </details>
            </div>
          )}
          {!loading && !message && items.length === 0 && (
            <Surface>
              <Section title="本地工具状态" ariaLabel="本地工具状态">
                <EmptyState
                  compact
                  icon={Package}
                  title="本地工具目录为空"
                  description="本地职业核心已连接，但没有可展示的工具；安装工具后会显示在这里。"
                />
              </Section>
            </Surface>
          )}
        </>
      )}

      {tab === "tools" && items.length > 0 && (
        <Surface>
          <Section title="本地工具状态" description="每个工具的权限、健康与更新策略；默认无外部写入。" meta={`${items.length} 个工具`}>
            <div className="plugin-grid" aria-label="工具目录">
              {items.map((item) => (
                <article className="plugin-card" key={item.manifest.id}>
                  <div className="plugin-card__head">
                    <div className="plugin-icon" aria-hidden="true"><Package size={17} /></div>
                    <div>
                      <h2>{toolName(item)}</h2>
                      <p>版本 {item.manifest.version}</p>
                    </div>
                    <span className={item.installation?.enabled ? "badge badge--green" : "badge"}>
                      {item.installation?.enabled ? <ShieldCheck size={12} aria-hidden="true" /> : <XCircle size={12} aria-hidden="true" />}
                      {statusLabel(item)}
                    </span>
                  </div>
                  <p className="plugin-description">{toolDescription(item)}</p>
                  <dl className="dl plugin-meta">
                    <div><dt>类型</dt><dd>{displayLabel(item.manifest.type)}</dd></div>
                    <div><dt>许可证</dt><dd>{item.manifest.source.license}</dd></div>
                    <div><dt>固定来源</dt><dd title={item.manifest.source.commit}>{item.manifest.source.ref}</dd></div>
                    <div><dt>健康</dt><dd>{displayLabel(item.installation?.last_health_status, "未检查")}</dd></div>
                    <div><dt>离线扫描</dt><dd>{item.release_scan?.overall === "passed" ? "通过" : "隔离"}</dd></div>
                  </dl>
                  <div className="plugin-chips">
                    {item.manifest.capabilities.map((capability) => <span key={capability}>{displayLabel(capability)}</span>)}
                  </div>
                  <p className="plugin-permissions">
                    <HeartPulse size={13} aria-hidden="true" />
                    {item.manifest.permissions.external_write ? "包含外部写入（需审批）" : "默认无外部写入"}
                  </p>
                  <details className="disclosure">
                    <summary>查看详情与权限</summary>
                    <div className="disclosure__body">
                      <dl className="dl">
                        <div><dt>仓库</dt><dd>{item.manifest.source.repo}</dd></div>
                        <div><dt>固定代码版本</dt><dd>{item.manifest.source.commit}</dd></div>
                        <div><dt>网络</dt><dd>{item.manifest.permissions.network.join(", ") || "无"}</dd></div>
                        <div><dt>文件</dt><dd>{item.manifest.permissions.filesystem.join(", ") || "无"}</dd></div>
                        <div><dt>密钥权限</dt><dd>{item.manifest.permissions.secrets.join(", ") || "无"}</dd></div>
                        <div><dt>数据范围</dt><dd>{item.manifest.permissions.scope.join(", ") || "无"}</dd></div>
                        <div><dt>许可证复核</dt><dd>{displayLabel(item.release_scan?.license?.manual_review_status)}</dd></div>
                        <div><dt>许可证声明要求</dt><dd>{displayLabel(item.release_scan?.license?.notice_requirement)}</dd></div>
                        <div><dt>依赖扫描</dt><dd>{displayLabel(item.release_scan?.dependencies?.scan_mode)}</dd></div>
                      </dl>
                    </div>
                  </details>
                  {item.installed && (
                    <label className="plugin-policy">
                      更新策略
                      <select
                        className="select"
                        aria-label={`${item.manifest.name}更新策略`}
                        value={item.installation?.config?.update_policy ?? "notify"}
                        disabled={Boolean(pending)}
                        onChange={(event) => void changePolicy(item, event.target.value as "notify" | "patch_auto" | "manual")}
                      >
                        <option value="notify">仅提醒</option>
                        <option value="patch_auto">准备补丁预览</option>
                        <option value="manual">手动批准</option>
                      </select>
                    </label>
                  )}
                  <div className="plugin-actions">
                    {!item.installed ? (
                      <Button size="sm" variant="primary" loading={Boolean(pending)} onClick={() => void act(item, "install")} icon={<Package size={13} aria-hidden="true" />}>安装</Button>
                    ) : (
                      <>
                        <Button size="sm" variant="secondary" loading={Boolean(pending)} disabled={item.installation?.status === "quarantined"} onClick={() => void act(item, item.installation?.enabled ? "disable" : "enable")} icon={<Power size={13} aria-hidden="true" />}>{item.installation?.enabled ? "停用" : "启用"}</Button>
                        <Button size="sm" variant="secondary" loading={Boolean(pending)} onClick={() => void act(item, "healthcheck")} icon={<HeartPulse size={13} aria-hidden="true" />}>健康检查</Button>
                        <Button size="sm" variant="secondary" loading={Boolean(pending)} onClick={() => void act(item, "update-preview")} icon={<RefreshCw size={13} aria-hidden="true" />}>更新预览</Button>
                        <Button size="sm" variant="secondary" loading={Boolean(pending)} onClick={() => void act(item, "rollback")} icon={<Undo2 size={13} aria-hidden="true" />}>回滚</Button>
                        <Button size="sm" variant="quiet" loading={Boolean(pending)} onClick={() => void showAudit(item)}>审计</Button>
                        <Button size="sm" variant="quiet" loading={Boolean(pending)} onClick={() => void showUninstallPreview(item)}>卸载影响</Button>
                      </>
                    )}
                  </div>
                  {auditPluginId === item.manifest.id && auditSummary && (
                    <section className="plugin-audit" aria-label={`${item.manifest.name}审计`}>
                      <h3>运行与生命周期审计</h3>
                      <p>运行 {auditSummary.run_count} 次 · 错误率 {auditSummary.error_rate} · 平均延迟 {auditSummary.latency.average_ms.toFixed(1)} ms</p>
                      <p>数据范围：{auditSummary.declared_data_scopes.join(", ") || "无"}</p>
                      <ol>
                        {auditEvents.slice(-8).map((event) => <li key={event.audit_id}>{displayLabel(event.action)} · {displayLabel(event.actor)} · {event.occurred_at}</li>)}
                      </ol>
                    </section>
                  )}
                  {uninstallPreview?.plugin_id === item.manifest.id && (
                    <section className="plugin-audit" aria-label={`${item.manifest.name}卸载影响`}>
                      <h3>卸载影响预览</h3>
                      <p>{uninstallPreview.removal_allowed ? "停用后可以移除插件指针。" : "插件仍启用，暂不可移除。"}</p>
                      <p>Career Core 权威数据删除：{uninstallPreview.core_truth_deleted ? "会" : "不会"}；原始材料字节删除：{uninstallPreview.artifact_bytes_deleted ? "会" : "不会"}。</p>
                      <p>保留记录：{uninstallPreview.retained_records.join(", ")}</p>
                    </section>
                  )}
                </article>
              ))}
            </div>
          </Section>
        </Surface>
      )}
      {tab === "tasks" && <TaskQueuePanel />}
    </main>
  );
}
