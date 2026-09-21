import { useCallback, useEffect, useState } from "react";

import {
  configureModelProvider,
  listModelProviders,
  testModelProvider,
  type ModelProviderConfig,
  type ModelProviderInput,
  type ProviderKind,
} from "../api/modelProviders";

const definitions: Array<{ kind: ProviderKind; name: string; base_url: string; model: string }> = [
  { kind: "openai", name: "OpenAI", base_url: "https://api.openai.com/v1", model: "gpt-4.1-mini" },
  { kind: "anthropic", name: "Anthropic", base_url: "https://api.anthropic.com/v1", model: "claude-sonnet-4-5" },
  { kind: "deepseek", name: "DeepSeek", base_url: "https://api.deepseek.com/v1", model: "deepseek-chat" },
  { kind: "openai_compatible", name: "OpenAI 兼容接口", base_url: "http://127.0.0.1:11434/v1", model: "本地模型名称" },
];

const statusLabel = (status?: ModelProviderConfig["connection_status"]) => ({
  connected: "已连接",
  failed: "连接失败",
  not_tested: "尚未测试",
  unconfigured: "尚未配置",
}[status ?? "unconfigured"]);

export function ModelProvidersPanel() {
  const [items, setItems] = useState<ModelProviderConfig[]>([]);
  const [drafts, setDrafts] = useState<Record<string, ModelProviderInput>>({});
  const [keys, setKeys] = useState<Record<string, string>>({});
  const [confirmed, setConfirmed] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState("");
  const [pending, setPending] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const loaded = await listModelProviders();
      if (!signal?.aborted) setItems(loaded);
    } catch (error) {
      if (!signal?.aborted) setMessage(`模型配置读取失败：${(error as Error).message}`);
    }
  }, []);

  useEffect(() => { const controller = new AbortController(); void load(controller.signal); return () => controller.abort(); }, [load]);

  const draftFor = (kind: ProviderKind): ModelProviderInput => {
    const definition = definitions.find((item) => item.kind === kind)!;
    const saved = items.find((item) => item.provider_id === kind);
    return drafts[kind] ?? {
      provider_id: kind,
      provider_kind: kind,
      base_url: saved?.base_url ?? definition.base_url,
      default_model: saved?.default_model ?? definition.model,
      timeout_seconds: saved?.timeout_seconds ?? 30,
    };
  };

  const patchDraft = (kind: ProviderKind, patch: Partial<ModelProviderInput>) => {
    setDrafts((old) => ({ ...old, [kind]: { ...draftFor(kind), ...patch } }));
  };

  async function save(kind: ProviderKind) {
    setPending(`${kind}:save`); setMessage("");
    try {
      const apiKey = keys[kind]?.trim();
      await configureModelProvider({ ...draftFor(kind), ...(apiKey ? { api_key: apiKey } : {}) });
      setKeys((old) => ({ ...old, [kind]: "" }));
      setMessage("配置已保存到本机；连接测试通过前不会显示为已连接。");
      await load();
    } catch (error) { setMessage(`保存失败：${(error as Error).message}`); }
    finally { setPending(""); }
  }

  async function test(kind: ProviderKind) {
    setPending(`${kind}:test`); setMessage("");
    try {
      const result = await testModelProvider(kind);
      setMessage(result.test.success ? "真实连通性测试通过。" : "连接失败，请检查服务地址、密钥和网络。未发送职业数据。");
      await load();
    } catch (error) { setMessage(`连接测试失败：${(error as Error).message}`); }
    finally { setPending(""); }
  }

  return <section className="model-providers" aria-labelledby="model-provider-title">
    <div className="page-heading model-providers__heading">
      <div><p className="eyebrow">模型服务</p><h2 id="model-provider-title">模型服务配置</h2><p>密钥保存在 Windows 凭据管理器，页面和日志不会显示明文。</p></div>
    </div>
    {message && <p role="status" className="plugin-action-message">{message}</p>}
    <div className="plugin-grid model-provider-grid">
      {definitions.map((definition) => {
        const saved = items.find((item) => item.provider_id === definition.kind);
        const draft = draftFor(definition.kind);
        return <article className="plugin-card" key={definition.kind}>
          <div className="plugin-card-header"><div><h3>{definition.name}</h3><p>{statusLabel(saved?.connection_status)}</p></div><span className="plugin-status">{saved?.has_api_key ? "密钥已保存" : "尚无密钥"}</span></div>
          <label>服务地址<input value={draft.base_url} onChange={(event) => patchDraft(definition.kind, { base_url: event.target.value })} /></label>
          <label>默认模型<input value={draft.default_model} onChange={(event) => patchDraft(definition.kind, { default_model: event.target.value })} /></label>
          <label>API 密钥<input type="password" autoComplete="new-password" value={keys[definition.kind] ?? ""} placeholder={saved?.has_api_key ? "已安全保存；留空表示不更换" : "输入后仅保存到系统安全存储"} onChange={(event) => setKeys((old) => ({ ...old, [definition.kind]: event.target.value }))} /></label>
          <label>超时（秒）<input type="number" min="1" max="120" value={draft.timeout_seconds} onChange={(event) => patchDraft(definition.kind, { timeout_seconds: Number(event.target.value) })} /></label>
          <p className="model-provider-notice">连接测试只请求模型列表；服务方会收到网络地址和请求元数据，不发送简历、岗位或项目内容。</p>
          <label className="model-provider-confirm"><input type="checkbox" checked={confirmed[definition.kind] ?? false} onChange={(event) => setConfirmed((old) => ({ ...old, [definition.kind]: event.target.checked }))} />我确认执行一次外部连接请求</label>
          <div className="plugin-actions"><button type="button" disabled={Boolean(pending)} onClick={() => void save(definition.kind)}>保存配置</button><button type="button" disabled={Boolean(pending) || !saved || (!saved.has_api_key && definition.kind !== "openai_compatible") || !confirmed[definition.kind]} onClick={() => void test(definition.kind)}>测试连接</button></div>
        </article>;
      })}
    </div>
  </section>;
}
