import { useCallback, useEffect, useMemo, useState } from "react";
import { PencilLine, Plus, Search, Zap } from "lucide-react";

import {
  configureModelProvider,
  listModelProviders,
  testModelProvider,
  type ModelProviderConfig,
} from "../api/modelProviders";
import { PROVIDER_PRESETS, presetById, type ProviderPreset } from "../api/providerPresets";
import { Button } from "../components/ui/Button";
import { Drawer } from "../components/ui/Drawer";
import { ErrorNotice, InlineNotice } from "../components/ui/Notice";
import { Field } from "../components/ui/Field";
import { ProviderMark } from "../components/ui/ProviderMark";

const statusLabel = (status?: ModelProviderConfig["connection_status"]) => ({
  connected: "已连接",
  failed: "连接失败",
  not_tested: "尚未测试",
  unconfigured: "尚未配置",
}[status ?? "unconfigured"]);

const statusTone = (status?: ModelProviderConfig["connection_status"]) => ({
  connected: "badge badge--green",
  failed: "badge badge--danger",
  not_tested: "badge badge--gold",
  unconfigured: "badge",
}[status ?? "unconfigured"]);

interface DrawerState {
  preset: ProviderPreset;
  existing: ModelProviderConfig | null;
}

export function ModelProvidersPanel() {
  const [items, setItems] = useState<ModelProviderConfig[]>([]);
  const [drawer, setDrawer] = useState<DrawerState | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("");
  const [customModel, setCustomModel] = useState("");
  const [timeoutSeconds, setTimeoutSeconds] = useState(30);
  const [confirmed, setConfirmed] = useState(false);
  const [presetQuery, setPresetQuery] = useState("");
  const [message, setMessage] = useState("");
  const [messageDetail, setMessageDetail] = useState("");
  const [pending, setPending] = useState("");
  const [tab, setTab] = useState<"configured" | "add" | "local" | "advanced">("configured");

  const load = useCallback(async (signal?: AbortSignal) => {
    try {
      const loaded = await listModelProviders();
      if (!signal?.aborted) setItems(loaded);
    } catch (error) {
      if (!signal?.aborted) {
        setMessage("模型配置读取失败，请确认本地服务已启动。");
        setMessageDetail((error as Error).message);
      }
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void load(controller.signal);
    return () => controller.abort();
  }, [load]);

  const configuredIds = useMemo(() => new Set(items.map((item) => item.provider_id)), [items]);

  const openDrawer = (preset: ProviderPreset, existing: ModelProviderConfig | null) => {
    setDrawer({ preset, existing });
    setApiKey("");
    setBaseUrl(existing?.base_url ?? preset.baseUrl);
    setModel(existing?.default_model ?? preset.recommendedModel);
    setCustomModel("");
    setTimeoutSeconds(existing?.timeout_seconds ?? 30);
    setConfirmed(false);
    setMessage("");
    setMessageDetail("");
  };

  const closeDrawer = () => setDrawer(null);

  const availablePresets = useMemo(() => {
    const query = presetQuery.trim().toLowerCase();
    return PROVIDER_PRESETS.filter((preset) => !configuredIds.has(preset.id))
      .filter((preset) => !query || preset.name.toLowerCase().includes(query) || preset.note.toLowerCase().includes(query));
  }, [configuredIds, presetQuery]);

  const cloudPresets = availablePresets.filter((preset) => !preset.isLocal && !preset.id.startsWith("custom-"));
  const localPresets = availablePresets.filter((preset) => preset.isLocal);
  const customPresets = availablePresets.filter((preset) => preset.id.startsWith("custom-"));

  async function save() {
    if (!drawer) return;
    const { preset, existing } = drawer;
    const finalModel = model === "__custom" ? customModel.trim() : model;
    if (!baseUrl.trim() || !finalModel) {
      setMessage("请填写服务地址与默认模型。");
      return;
    }
    setPending("save");
    setMessage("");
    setMessageDetail("");
    try {
      const key = apiKey.trim();
      await configureModelProvider({
        provider_id: preset.id,
        provider_kind: preset.kind,
        base_url: baseUrl.trim(),
        default_model: finalModel,
        timeout_seconds: timeoutSeconds,
        ...(key ? { api_key: key } : {}),
      });
      setApiKey("");
      setMessage("配置已保存到本机；连接测试通过前不会显示为已连接。");
      await load();
      setDrawer(null);
      setTab("configured");
    } catch (error) {
      setMessage("保存配置失败，请重试。");
      setMessageDetail((error as Error).message);
    } finally {
      setPending("");
    }
  }

  async function test() {
    if (!drawer) return;
    const { preset } = drawer;
    setPending("test");
    setMessage("");
    setMessageDetail("");
    try {
      const result = await testModelProvider(preset.id);
      setMessage(result.test.success ? "真实连通性测试通过。" : "连接失败，请检查服务地址、密钥和网络。未发送职业数据。");
      await load();
      setDrawer(null);
      setTab("configured");
    } catch (error) {
      setMessage("连接测试失败，请重试。");
      setMessageDetail((error as Error).message);
    } finally {
      setPending("");
    }
  }

  const drawerConfigured = drawer ? (drawer.existing ?? items.find((item) => item.provider_id === drawer.preset.id)) ?? null : null;
  const canTest = Boolean(drawer && drawerConfigured && confirmed && drawer.preset.supportsTest);

  return (
    <div className="provider-workbench">
      {message && !drawer && (
        <div style={{ marginBottom: "var(--space-4)" }}>
          {messageDetail
            ? <ErrorNotice label={message} detail={messageDetail} />
            : <InlineNotice tone={message.includes("失败") || message.includes("请填写") ? "danger" : "success"} role="status">{message}</InlineNotice>}
        </div>
      )}

      <div className="tab-bar tab-bar--inset" role="tablist" aria-label="模型服务分区">
        <button type="button" role="tab" aria-selected={tab === "configured"} onClick={() => setTab("configured")}>已配置{items.length > 0 ? ` (${items.length})` : ""}</button>
        <button type="button" role="tab" aria-selected={tab === "add"} onClick={() => setTab("add")}>添加厂商</button>
        <button type="button" role="tab" aria-selected={tab === "local"} onClick={() => setTab("local")}>本地模型</button>
        <button type="button" role="tab" aria-selected={tab === "advanced"} onClick={() => setTab("advanced")}>高级配置</button>
      </div>

      {tab === "configured" && <div className="provider-section">
        <div className="provider-section__head">
          <h3>已配置</h3>
          <span className="section__meta">{items.length} 个服务</span>
          <span className="topbar__spacer" />
          <Button size="sm" variant="primary" icon={<Plus size={14} aria-hidden="true" />} onClick={() => document.getElementById("provider-preset-search")?.focus()}>添加模型服务</Button>
        </div>
        {items.length === 0 ? (
          <p className="text-aux">尚未配置模型服务。从下方“可添加厂商”选择一个预设，只需填入 API Key。</p>
        ) : (
          <div className="provider-card-grid">
            {items.map((item) => {
              const preset = presetById(item.provider_id);
              return (
                <article className="provider-card" key={item.provider_id}>
                  <div className="provider-card__head">
                    <ProviderMark presetId={item.provider_id} />
                    <div className="provider-card__id">
                      <h4>{preset?.name ?? item.provider_id}</h4>
                      <p>{preset?.kindLabel ?? item.provider_kind} · {item.default_model}</p>
                    </div>
                    <span className={statusTone(item.connection_status)}>{statusLabel(item.connection_status)}</span>
                  </div>
                  <dl className="dl">
                    <div><dt>服务地址</dt><dd>{item.base_url}</dd></div>
                    <div><dt>API 密钥</dt><dd>{item.has_api_key ? "已安全保存（不显示明文）" : "尚未配置"}</dd></div>
                    {item.last_checked_at && <div><dt>最近测试</dt><dd>{item.last_checked_at}</dd></div>}
                  </dl>
                  <div className="plugin-actions">
                    <Button size="sm" variant="secondary" icon={<PencilLine size={13} aria-hidden="true" />} onClick={() => openDrawer(preset ?? {
                      id: item.provider_id, name: item.provider_id, kind: item.provider_kind, kindLabel: item.provider_kind,
                      baseUrl: item.base_url, recommendedModel: item.default_model, models: [],
                      supportsTest: true, isLocal: false, helpUrl: "", note: "",
                    }, item)}>编辑</Button>
                    <Button
                      size="sm"
                      variant="secondary"
                      icon={<Zap size={13} aria-hidden="true" />}
                      disabled={!item.has_api_key && item.provider_kind !== "openai_compatible"}
                      onClick={() => openDrawer(preset ?? {
                        id: item.provider_id, name: item.provider_id, kind: item.provider_kind, kindLabel: item.provider_kind,
                        baseUrl: item.base_url, recommendedModel: item.default_model, models: [],
                        supportsTest: true, isLocal: false, helpUrl: "", note: "",
                      }, item)}
                    >
                      测试连接
                    </Button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>}

      {tab === "add" && <div className="provider-section">
        <div className="provider-section__head">
          <h3>可添加厂商</h3>
          <span className="provider-search">
            <Search size={14} aria-hidden="true" />
            <input
              id="provider-preset-search"
              aria-label="搜索厂商预设"
              placeholder="搜索厂商…"
              value={presetQuery}
              onChange={(event) => setPresetQuery(event.target.value)}
            />
          </span>
        </div>
        {cloudPresets.length === 0 && <p className="text-aux">没有匹配的厂商预设。</p>}
        <div className="provider-card-grid">
          {cloudPresets.map((preset) => (
            <button type="button" className="provider-card provider-card--preset" key={preset.id} onClick={() => openDrawer(preset, null)}>
              <span className="provider-card__head">
                <ProviderMark presetId={preset.id} />
                <span className="provider-card__id">
                  <h4>{preset.name}</h4>
                  <p>{preset.kindLabel}</p>
                </span>
                <Plus size={15} aria-hidden="true" />
              </span>
              <span className="provider-card__note">{preset.note}</span>
            </button>
          ))}
        </div>
      </div>}

      {tab === "local" && localPresets.length === 0 && <p className="text-aux">本地模型厂商已全部配置。</p>}
      {tab === "local" && localPresets.length > 0 && (
        <div className="provider-section">
          <div className="provider-section__head"><h3>本地模型</h3><span className="badge">本机运行 · 不出网</span></div>
          <div className="provider-card-grid">
            {localPresets.map((preset) => (
              <button type="button" className="provider-card provider-card--preset provider-card--local" key={preset.id} onClick={() => openDrawer(preset, null)}>
                <span className="provider-card__head">
                  <ProviderMark presetId={preset.id} />
                  <span className="provider-card__id">
                    <h4>{preset.name}</h4>
                    <p>{preset.kindLabel}</p>
                  </span>
                  <Plus size={15} aria-hidden="true" />
                </span>
                <span className="provider-card__note">{preset.note}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {tab === "advanced" && (
        <div className="provider-section">
          <p className="text-aux">自定义兼容服务用于注册表之外的端点；与预设一样写入系统安全存储。</p>
          <div className="provider-card-grid">
              {customPresets.map((preset) => (
                <button type="button" className="provider-card provider-card--preset" key={preset.id} onClick={() => openDrawer(preset, null)}>
                  <span className="provider-card__head">
                    <ProviderMark presetId={preset.id} />
                    <span className="provider-card__id">
                      <h4>{preset.name}</h4>
                      <p>{preset.kindLabel}</p>
                    </span>
                    <Plus size={15} aria-hidden="true" />
                  </span>
                  <span className="provider-card__note">{preset.note}</span>
                </button>
              ))}
          </div>
        </div>
      )}

      <Drawer
        open={drawer !== null}
        onClose={closeDrawer}
        ariaLabel={drawer ? (drawer.existing ? `编辑 ${drawer.preset.name}` : `添加 ${drawer.preset.name}`) : undefined}
        title={drawer ? (
          <span className="drawer-title">
            <ProviderMark presetId={drawer.preset.id} size={26} />
            {drawer.existing ? `编辑 ${drawer.preset.name}` : `添加 ${drawer.preset.name}`}
          </span>
        ) : null}
        footer={drawer ? (
          <>
            <Button variant="quiet" onClick={closeDrawer}>取消</Button>
            <Button
              variant="secondary"
              loading={pending === "test"}
              disabled={!canTest}
              icon={<Zap size={14} aria-hidden="true" />}
              onClick={() => void test()}
            >
              测试连接
            </Button>
            <Button
              variant="primary"
              loading={pending === "save"}
              onClick={() => void save()}
            >
              保存配置
            </Button>
          </>
        ) : null}
      >
        {drawer ? (
          <>
            <p className="text-aux">{drawer.preset.note}密钥保存在 Windows 凭据管理器，页面和日志不会显示明文。</p>
            <Field label="API 密钥" helper={drawerConfigured?.has_api_key ? "已安全保存；留空表示不更换。" : "必填，仅保存到系统安全存储。"}>
              <input
                className="input"
                type="password"
                autoComplete="new-password"
                aria-label="API 密钥"
                value={apiKey}
                placeholder={drawerConfigured?.has_api_key ? "已安全保存；留空表示不更换" : "输入 API Key"}
                onChange={(event) => setApiKey(event.target.value)}
              />
            </Field>
            <Field label="默认模型" helper="可从推荐列表选择，或手动填写模型 ID。">
              {drawer.preset.models.length > 0 ? (
                <select
                  className="select"
                  aria-label="默认模型"
                  value={model}
                  onChange={(event) => setModel(event.target.value)}
                >
                  {drawer.preset.models.map((item) => <option key={item} value={item}>{item}{item === drawer.preset.recommendedModel ? "（推荐）" : ""}</option>)}
                  <option value="__custom">自定义模型 ID…</option>
                </select>
              ) : (
                <input
                  className="input"
                  aria-label="默认模型"
                  value={model}
                  placeholder={drawer.preset.isLocal ? "本机已加载的模型名" : "模型 ID"}
                  onChange={(event) => setModel(event.target.value)}
                />
              )}
            </Field>
            {model === "__custom" && (
              <Field label="自定义模型 ID">
                <input className="input" value={customModel} onChange={(event) => setCustomModel(event.target.value)} placeholder="输入模型 ID" />
              </Field>
            )}
            <details className="disclosure">
              <summary>高级设置（服务地址、超时）</summary>
              <div className="disclosure__body drawer-advanced">
                <Field label="服务地址">
                  <input className="input" value={baseUrl} onChange={(event) => setBaseUrl(event.target.value)} />
                </Field>
                <Field label="超时（秒）">
                  <input
                    className="input"
                    type="number"
                    min="1"
                    max="120"
                    value={timeoutSeconds}
                    onChange={(event) => setTimeoutSeconds(Number(event.target.value))}
                  />
                </Field>
              </div>
            </details>
            {drawer.preset.supportsTest && (
              <label className="checkbox">
                <input type="checkbox" checked={confirmed} onChange={(event) => setConfirmed(event.target.checked)} />
                我确认执行一次外部连接请求
              </label>
            )}
            {!drawerConfigured && (
              <InlineNotice tone="muted">保存配置后才能测试连接；连接测试只请求模型列表，不发送简历、岗位或项目内容。</InlineNotice>
            )}
            {message && drawer && (
              messageDetail
                ? <ErrorNotice label={message} detail={messageDetail} />
                : <InlineNotice tone={message.includes("失败") || message.includes("请填写") ? "danger" : "muted"} role="status">{message}</InlineNotice>
            )}
          </>
        ) : null}
      </Drawer>
    </div>
  );
}
