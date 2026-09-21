import { useEffect, useState } from "react";
import { HeartPulse, Package, ShieldCheck, XCircle } from "lucide-react";

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

  useEffect(() => {
    let active = true;
    apiRequest<PluginCatalogItem[]>("/api/v1/plugins")
      .then((data) => {
        if (!active) return;
        setItems(data);
        setMessage("");
      })
      .catch((error: Error) => {
        if (active) setMessage("插件目录暂不可用：" + error.message);
      });
    return () => {
      active = false;
    };
  }, []);

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
          </article>
        ))}
      </section>
    </main>
  );
}
