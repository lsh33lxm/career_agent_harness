import { useCallback, useEffect, useState } from "react";
import { HeartPulse, Package, Power, RefreshCw, ShieldCheck, Undo2, XCircle } from "lucide-react";

import { apiRequest } from "../api/client";
import type { PluginCatalogItem } from "../api/plugins";

function statusLabel(item: PluginCatalogItem): string {
  if (!item.installed) return "未安装";
  if (item.installation?.enabled) return "已启用";
  return item.installation?.status === "rolled_back" ? "已回滚" : "已停用";
}

export function PluginsPage() {
  const [items, setItems] = useState<PluginCatalogItem[]>([]);
  const [message, setMessage] = useState("正在读取插件目录…");
  const [pending, setPending] = useState("");
  const [actionMessage, setActionMessage] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      setItems(await apiRequest<PluginCatalogItem[]>("/api/v1/plugins", { signal }));
      setMessage("");
    } catch (error) {
      if (!signal?.aborted) setMessage("插件目录暂不可用：" + (error as Error).message);
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

  return (
    <main className="page plugins-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Extensions</p>
          <h1>插件</h1>
        </div>
        <span className="service-status"><Package size={16} />本地目录</span>
      </div>
      {message && <div className="empty-state"><p>{message}</p></div>}
      {actionMessage && <p className="plugin-action-message" role="status">{actionMessage}</p>}
      <section className="plugin-grid" aria-label="插件目录">
        {items.map((item) => (
          <article className="plugin-card" key={item.manifest.id}>
            <div className="plugin-card-header">
              <div className="plugin-icon" aria-hidden="true"><Package size={19} /></div>
              <div>
                <h2>{item.manifest.name}</h2>
                <p>{item.manifest.id} · v{item.manifest.version}</p>
              </div>
              <span className="plugin-status">
                {item.installation?.enabled ? <ShieldCheck size={14} /> : <XCircle size={14} />}
                {statusLabel(item)}
              </span>
            </div>
            <p className="plugin-description">{item.manifest.user_visible_description}</p>
            <dl className="plugin-meta">
              <div><dt>类型</dt><dd>{item.manifest.type}</dd></div>
              <div><dt>许可证</dt><dd>{item.manifest.source.license}</dd></div>
              <div><dt>固定来源</dt><dd title={item.manifest.source.commit}>{item.manifest.source.ref}</dd></div>
              <div><dt>健康</dt><dd>{item.installation?.last_health_status ?? "未检查"}</dd></div>
            </dl>
            <div className="plugin-chips">
              {item.manifest.capabilities.map((capability) => <span key={capability}>{capability}</span>)}
            </div>
            <div className="plugin-permissions">
              <HeartPulse size={14} />
              {item.manifest.permissions.external_write ? "包含外部写入（需审批）" : "默认无外部写入"}
            </div>
            <div className="plugin-actions">
              {!item.installed ? (
                <button type="button" disabled={Boolean(pending)} onClick={() => void act(item, "install")}><Package size={14} />安装</button>
              ) : (
                <>
                  <button type="button" disabled={Boolean(pending) || item.installation?.status === "quarantined"} onClick={() => void act(item, item.installation?.enabled ? "disable" : "enable")}><Power size={14} />{item.installation?.enabled ? "停用" : "启用"}</button>
                  <button type="button" disabled={Boolean(pending)} onClick={() => void act(item, "healthcheck")}><HeartPulse size={14} />健康检查</button>
                  <button type="button" disabled={Boolean(pending)} onClick={() => void act(item, "update-preview")}><RefreshCw size={14} />更新预览</button>
                  <button type="button" disabled={Boolean(pending)} onClick={() => void act(item, "rollback")}><Undo2 size={14} />回滚</button>
                </>
              )}
            </div>
          </article>
        ))}
      </section>
    </main>
  );
}
