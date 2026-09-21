import { DatabaseZap, FolderSync, Pause, Play, RefreshCw } from "lucide-react";
import { FormEvent, useCallback, useEffect, useState } from "react";

import {
  createLocalFolderConnector,
  listSourceConnectors,
  listSourceSyncRuns,
  setSourceConnectorPaused,
  syncSourceConnector,
  testSourceConnector,
  type SourceConnector,
  type SourceSyncRun,
} from "../api/sourceConnectors";

const date = (value: string | null | undefined) => value
  ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value))
  : "尚未同步";

const connectorTypeLabels: Record<SourceConnector["connector_type"], string> = {
  local_folder: "本地文件夹",
  legacy_agent_radar: "Legacy 历史数据",
  github: "GitHub 只读仓库",
};

function connectorLocation(connector: SourceConnector): string {
  return connector.config.repository_url ?? connector.config.root_path ?? "未记录定位信息";
}

export function SourceConnectorsPanel() {
  const [connectors, setConnectors] = useState<SourceConnector[]>([]);
  const [runs, setRuns] = useState<Record<string, SourceSyncRun | undefined>>({});
  const [displayName, setDisplayName] = useState("");
  const [rootPath, setRootPath] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [message, setMessage] = useState("本地资料只读同步，源文件不会被修改或删除。");

  const refresh = useCallback(async (signal?: AbortSignal) => {
    const items = await listSourceConnectors(signal);
    setConnectors(items);
    const histories = await Promise.all(items.map(async (item) => ({
      id: item.connector_id,
      run: (await listSourceSyncRuns(item.connector_id, signal))[0],
    })));
    setRuns(Object.fromEntries(histories.map((item) => [item.id, item.run])));
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    refresh(controller.signal).catch((error: Error) => {
      if (!controller.signal.aborted) setMessage(`资料源暂不可用：${error.message}`);
    });
    return () => controller.abort();
  }, [refresh]);

  async function create(event: FormEvent) {
    event.preventDefault();
    if (!displayName.trim() || !rootPath.trim()) return;
    setBusy("create");
    try {
      await createLocalFolderConnector(displayName.trim(), rootPath.trim());
      setDisplayName(""); setRootPath("");
      await refresh();
      setMessage("本地资料源已添加。首次同步前可先测试连接。");
    } catch (error) {
      setMessage(`添加失败：${(error as Error).message}`);
    } finally { setBusy(null); }
  }

  async function operate(connector: SourceConnector, action: "test" | "sync" | "toggle") {
    setBusy(`${connector.connector_id}:${action}`);
    try {
      if (action === "test") {
        const result = await testSourceConnector(connector.connector_id);
        setMessage(
          connector.connector_type === "github" && !result.network_verified
            ? `“${connector.display_name}”配置有效，尚未完成真实只读网络验证。`
            : `“${connector.display_name}”连接正常。`,
        );
      } else if (action === "sync") {
        const task = await syncSourceConnector(connector.connector_id);
        setMessage(task.status === "completed" ? `“${connector.display_name}”同步完成。` : `同步状态：${task.status}`);
      } else {
        await setSourceConnectorPaused(connector.connector_id, connector.status === "active");
        setMessage(connector.status === "active" ? "资料源已暂停。" : "资料源已恢复。兼容性检查通过后可手动同步。");
      }
      await refresh();
    } catch (error) {
      setMessage(`操作失败：${(error as Error).message}`);
    } finally { setBusy(null); }
  }

  return (
    <section className="source-connectors" aria-label="资料源">
      <div className="knowledge-section-heading">
        <div><p className="eyebrow">知识来源</p><h2>资料源</h2></div>
        <FolderSync size={20} />
      </div>
      <p className="knowledge-message">{message}</p>
      <form className="source-connector-form" onSubmit={create}>
        <label>资料源名称<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} placeholder="例如：我的求职资料" /></label>
        <label>本地文件夹路径<input value={rootPath} onChange={(event) => setRootPath(event.target.value)} placeholder="例如：D:\求职资料" /></label>
        <button type="submit" disabled={busy !== null || !displayName.trim() || !rootPath.trim()}>添加资料源</button>
      </form>
      <div className="source-connector-list">
        {connectors.length === 0 && <p className="knowledge-message">尚未添加资料源。添加后可进行只读、可追溯的增量同步。</p>}
        {connectors.map((connector) => {
          const latest = runs[connector.connector_id];
          const locked = busy?.startsWith(connector.connector_id) ?? false;
          return (
            <article key={connector.connector_id} className="source-connector-card">
              <div><DatabaseZap size={18} /><div><h3>{connector.display_name}</h3><p>{connectorTypeLabels[connector.connector_type]} · <span title={connectorLocation(connector)}>{connectorLocation(connector)}</span></p></div></div>
              <dl>
                <div><dt>状态</dt><dd>{connector.status === "active" ? "已启用" : "已暂停"}</dd></div>
                <div><dt>最近同步</dt><dd>{date(latest?.finished_at)}</dd></div>
                <div><dt>结果</dt><dd>{latest ? `新增 ${latest.stats.created} · 更新 ${latest.stats.updated} · 跳过 ${latest.stats.skipped} · 源端删除 ${latest.stats.deleted}` : "暂无记录"}</dd></div>
              </dl>
              <div className="source-connector-actions">
                <button onClick={() => operate(connector, "test")} disabled={locked}>测试连接</button>
                <button onClick={() => operate(connector, "sync")} disabled={locked || connector.status === "paused"}><RefreshCw size={15} />立即同步</button>
                <button onClick={() => operate(connector, "toggle")} disabled={locked}>{connector.status === "active" ? <><Pause size={15} />暂停</> : <><Play size={15} />恢复</>}</button>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
