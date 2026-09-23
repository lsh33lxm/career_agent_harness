import { useCallback, useEffect, useState } from "react";
import { HeartPulse, Package, Power, RefreshCw, ShieldCheck, Undo2, XCircle } from "lucide-react";

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
import { ModelProvidersPanel } from "./ModelProvidersPanel";
import { TaskQueuePanel } from "./TaskQueuePanel";

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
  const [auditPluginId, setAuditPluginId] = useState("");
  const [auditEvents, setAuditEvents] = useState<PluginAuditEvent[]>([]);
  const [auditSummary, setAuditSummary] = useState<PluginAuditSummary | null>(null);
  const [uninstallPreview, setUninstallPreview] = useState<PluginUninstallPreview | null>(null);

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
    try {
      const path = action === "install" ? "/api/v1/plugins/install" : `/api/v1/plugins/${encodeURIComponent(item.manifest.id)}/${action}`;
      const body = action === "install" ? JSON.stringify({ manifest: item.manifest }) : action === "update-preview" ? JSON.stringify({ fixture: {} }) : undefined;
      const result = await apiRequest<Record<string, unknown>>(path, { method: "POST", ...(body ? { body } : {}) });
      setActionMessage(`${item.manifest.name}：${action === "update-preview" ? (result.tests as { safe_to_switch?: boolean })?.safe_to_switch ? "更新检查通过" : "更新已隔离" : "操作完成"}`);
      await load();
    } catch (error) {
      setActionMessage(`${item.manifest.name}：${(error as Error).message}`);
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
    try {
      const [events, summary] = await Promise.all([
        listPluginAudit(item.manifest.id),
        getPluginAuditSummary(item.manifest.id),
      ]);
      setAuditPluginId(item.manifest.id);
      setAuditEvents(events);
      setAuditSummary(summary);
    } catch (error) {
      setActionMessage(`${item.manifest.name}：审计读取失败：${(error as Error).message}`);
    } finally {
      setPending("");
    }
  }

  async function showUninstallPreview(item: PluginCatalogItem) {
    setPending(`${item.manifest.id}:uninstall-preview`);
    setActionMessage("");
    try {
      setUninstallPreview(await previewPluginUninstall(item.manifest.id));
    } catch (error) {
      setActionMessage(`${item.manifest.name}：卸载影响读取失败：${(error as Error).message}`);
    } finally {
      setPending("");
    }
  }

  async function changePolicy(item: PluginCatalogItem, policy: "notify" | "patch_auto" | "manual") {
    setPending(`${item.manifest.id}:policy`);
    setActionMessage("");
    try {
      await setPluginUpdatePolicy(item.manifest.id, policy);
      setActionMessage(`${item.manifest.name}：更新策略已设为 ${displayLabel(policy)}`);
      await load();
    } catch (error) {
      setActionMessage(`${item.manifest.name}：更新策略保存失败：${(error as Error).message}`);
    } finally {
      setPending("");
    }
  }

  return (
    <main className="page plugins-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">本地接入</p>
          <h1>工具与模型</h1>
          <p>管理本地工具的权限、健康状态与更新。模型服务配置将在“模型服务”区域显示。</p>
        </div>
        <span className="service-status"><Package size={16} />本地目录</span>
      </div>
      {message && <div className="empty-state"><p>{message}</p></div>}
      {actionMessage && <p className="plugin-action-message" role="status">{actionMessage}</p>}
      <section className="plugin-grid" aria-label="工具目录">
        {items.map((item) => (
          <article className="plugin-card" key={item.manifest.id}>
            <div className="plugin-card-header">
              <div className="plugin-icon" aria-hidden="true"><Package size={19} /></div>
              <div>
                <h2>{toolName(item)}</h2>
                <p>版本 {item.manifest.version}</p>
              </div>
              <span className="plugin-status">
                {item.installation?.enabled ? <ShieldCheck size={14} /> : <XCircle size={14} />}
                {statusLabel(item)}
              </span>
            </div>
            <p className="plugin-description">{toolDescription(item)}</p>
            <dl className="plugin-meta">
              <div><dt>类型</dt><dd>{displayLabel(item.manifest.type)}</dd></div>
              <div><dt>许可证</dt><dd>{item.manifest.source.license}</dd></div>
              <div><dt>固定来源</dt><dd title={item.manifest.source.commit}>{item.manifest.source.ref}</dd></div>
              <div><dt>健康</dt><dd>{displayLabel(item.installation?.last_health_status, "未检查")}</dd></div>
              <div><dt>离线扫描</dt><dd>{item.release_scan?.overall === "passed" ? "通过" : "隔离"}</dd></div>
            </dl>
            <div className="plugin-chips">
              {item.manifest.capabilities.map((capability) => <span key={capability}>{displayLabel(capability)}</span>)}
            </div>
            <div className="plugin-permissions">
              <HeartPulse size={14} />
              {item.manifest.permissions.external_write ? "包含外部写入（需审批）" : "默认无外部写入"}
            </div>
            <details className="plugin-details">
              <summary>查看详情与权限</summary>
              <dl className="plugin-detail-list">
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
            </details>
            {item.installed && (
              <label className="plugin-policy">
                更新策略
                <select
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
                <button type="button" disabled={Boolean(pending)} onClick={() => void act(item, "install")}><Package size={14} />安装</button>
              ) : (
                <>
                  <button type="button" disabled={Boolean(pending) || item.installation?.status === "quarantined"} onClick={() => void act(item, item.installation?.enabled ? "disable" : "enable")}><Power size={14} />{item.installation?.enabled ? "停用" : "启用"}</button>
                  <button type="button" disabled={Boolean(pending)} onClick={() => void act(item, "healthcheck")}><HeartPulse size={14} />健康检查</button>
                  <button type="button" disabled={Boolean(pending)} onClick={() => void act(item, "update-preview")}><RefreshCw size={14} />更新预览</button>
                  <button type="button" disabled={Boolean(pending)} onClick={() => void act(item, "rollback")}><Undo2 size={14} />回滚</button>
                  <button type="button" disabled={Boolean(pending)} onClick={() => void showAudit(item)}>审计</button>
                  <button type="button" disabled={Boolean(pending)} onClick={() => void showUninstallPreview(item)}>卸载影响</button>
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
      </section>
      <ModelProvidersPanel />
      <TaskQueuePanel />
    </main>
  );
}
