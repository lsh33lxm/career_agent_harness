import { Database, DatabaseZap, FolderOpen, FolderSync, Github, Pause, Play, RefreshCw } from "lucide-react";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

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
import { displayLabel, syncStatusLabels } from "../app/displayLabels";
import { Section, Surface } from "../components/ui/Section";
import { Button } from "../components/ui/Button";
import { Field } from "../components/ui/Field";
import { ErrorNotice, InlineNotice } from "../components/ui/Notice";

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
  const [message, setMessage] = useState("");
  const [messageDetail, setMessageDetail] = useState("");

  const typeCounts = useMemo(() => ({
    local_folder: connectors.filter((item) => item.connector_type === "local_folder").length,
    github: connectors.filter((item) => item.connector_type === "github").length,
    legacy_agent_radar: connectors.filter((item) => item.connector_type === "legacy_agent_radar").length,
  }), [connectors]);

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
      if (!controller.signal.aborted) {
        setMessage("资料源暂不可用，请确认本地服务已启动。");
        setMessageDetail(error.message);
      }
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
      setMessageDetail("");
    } catch (error) {
      setMessage("添加资料源失败，请检查路径权限后重试。");
      setMessageDetail((error as Error).message);
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
        setMessage(task.status === "completed" ? `“${connector.display_name}”同步完成。` : `同步状态：${displayLabel(task.status, syncStatusLabels)}`);
      } else {
        await setSourceConnectorPaused(connector.connector_id, connector.status === "active");
        setMessage(connector.status === "active" ? "资料源已暂停。" : "资料源已恢复。兼容性检查通过后可手动同步。");
      }
      await refresh();
    } catch (error) {
      setMessage("资料源操作失败，请重试。");
      setMessageDetail((error as Error).message);
    } finally { setBusy(null); }
  }

  return (
    <Surface>
      <Section
        title="资料源"
        description="本地资料只读同步：需要读取权限的本地目录，源文件不会被修改或删除。"
        meta={<FolderSync size={16} aria-hidden="true" />}
      >
        <div className="connector-summary" aria-label="资料源概况">
          <span><FolderOpen size={14} aria-hidden="true" />本地文件 <strong>{typeCounts.local_folder}</strong> 个</span>
          <span><Github size={14} aria-hidden="true" />GitHub <strong>{typeCounts.github}</strong> 个仓库</span>
          <span><Database size={14} aria-hidden="true" />Legacy 历史 <strong>{typeCounts.legacy_agent_radar}</strong> 个</span>
          {connectors.some((item) => item.status === "active") && (
            <span className="connector-summary__ok"><FolderSync size={14} aria-hidden="true" />资料源已正常连接</span>
          )}
        </div>
        {message && (
        <div style={{ marginBottom: "var(--space-4)" }}>
          {messageDetail
            ? <ErrorNotice label={message} detail={messageDetail} />
            : <InlineNotice tone={message.includes("已添加") || message.includes("正常") || message.includes("完成") ? "success" : "muted"} role="status">{message}</InlineNotice>}
        </div>
        )}
        <form className="control-group control-group--connectors" onSubmit={(event) => void create(event)}>
          <Field label="资料源名称">
            <input
              className="input"
              value={displayName}
              onChange={(event) => setDisplayName(event.target.value)}
              placeholder="例如：我的求职资料"
            />
          </Field>
          <Field label="本地文件夹路径">
            <input
              className="input"
              value={rootPath}
              onChange={(event) => setRootPath(event.target.value)}
              placeholder="例如：D:\求职资料"
            />
          </Field>
          <Button variant="primary" type="submit" loading={busy === "create"} disabled={!displayName.trim() || !rootPath.trim()}>添加资料源</Button>
        </form>

        <div className="connector-list">
          {connectors.length === 0 && <p className="text-aux">尚未添加资料源。添加后可进行只读、可追溯的增量同步。</p>}
          {connectors.map((connector) => {
            const latest = runs[connector.connector_id];
            const locked = busy?.startsWith(connector.connector_id) ?? false;
            return (
              <article key={connector.connector_id} className="connector-card">
                <div className="connector-card__id">
                  <DatabaseZap size={16} aria-hidden="true" />
                  <div>
                    <h3>{connector.display_name}</h3>
                    <p>{connectorTypeLabels[connector.connector_type]} · <span title={connectorLocation(connector)}>{connectorLocation(connector)}</span></p>
                  </div>
                </div>
                <dl className="dl">
                  <div><dt>状态</dt><dd>{connector.status === "active" ? "已启用" : "已暂停"}</dd></div>
                  <div><dt>最近同步</dt><dd>{date(latest?.finished_at)}</dd></div>
                  <div><dt>结果</dt><dd>{latest ? `新增 ${latest.stats.created} · 更新 ${latest.stats.updated} · 跳过 ${latest.stats.skipped} · 源端删除 ${latest.stats.deleted}` : "暂无记录"}</dd></div>
                </dl>
                <div className="connector-card__actions">
                  <Button size="sm" variant="secondary" loading={busy === `${connector.connector_id}:test`} disabled={locked} onClick={() => void operate(connector, "test")}>测试连接</Button>
                  <Button size="sm" variant="secondary" loading={busy === `${connector.connector_id}:sync`} disabled={locked || connector.status === "paused"} onClick={() => void operate(connector, "sync")} icon={<RefreshCw size={13} aria-hidden="true" />}>立即同步</Button>
                  <Button size="sm" variant="quiet" loading={busy === `${connector.connector_id}:toggle`} disabled={locked} onClick={() => void operate(connector, "toggle")} icon={connector.status === "active" ? <Pause size={13} aria-hidden="true" /> : <Play size={13} aria-hidden="true" />}>
                    {connector.status === "active" ? "暂停" : "恢复"}
                  </Button>
                </div>
              </article>
            );
          })}
        </div>
      </Section>
    </Surface>
  );
}
