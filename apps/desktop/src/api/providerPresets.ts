import type { ProviderKind } from "./modelProviders";

/**
 * 厂商预设注册表（数据驱动）。
 * baseUrl / 推荐模型来自厂商官方文档与后端 PROVIDER_DEFAULTS；
 * 模型 ID 均为可编辑预填值，厂商更新模型后用户可直接修改。
 */
export interface ProviderPreset {
  id: string;
  name: string;
  kind: ProviderKind;
  kindLabel: string;
  baseUrl: string;
  recommendedModel: string;
  models: string[];
  supportsTest: boolean;
  isLocal: boolean;
  helpUrl: string;
  note: string;
}

export const PROVIDER_PRESETS: ProviderPreset[] = [
  {
    id: "openai", name: "OpenAI", kind: "openai", kindLabel: "OpenAI 协议",
    baseUrl: "https://api.openai.com/v1", recommendedModel: "gpt-4.1-mini",
    models: ["gpt-4.1-mini", "gpt-4.1", "gpt-4o-mini"],
    supportsTest: true, isLocal: false,
    helpUrl: "https://platform.openai.com/docs",
    note: "通用能力全面，适合多种任务场景。",
  },
  {
    id: "anthropic", name: "Anthropic", kind: "anthropic", kindLabel: "Anthropic 协议",
    baseUrl: "https://api.anthropic.com/v1", recommendedModel: "claude-sonnet-4-5",
    models: ["claude-sonnet-4-5", "claude-haiku-4-5"],
    supportsTest: true, isLocal: false,
    helpUrl: "https://docs.anthropic.com",
    note: "擅长长文本理解与分析，适合复杂推理任务。",
  },
  {
    id: "gemini", name: "Google Gemini", kind: "openai_compatible", kindLabel: "OpenAI 兼容",
    baseUrl: "https://generativelanguage.googleapis.com/v1beta/openai", recommendedModel: "gemini-2.5-flash",
    models: ["gemini-2.5-flash", "gemini-2.5-pro"],
    supportsTest: true, isLocal: false,
    helpUrl: "https://ai.google.dev/gemini-api/docs/openai",
    note: "通过 Gemini 官方 OpenAI 兼容端点接入。",
  },
  {
    id: "kimi", name: "Kimi / Moonshot", kind: "openai_compatible", kindLabel: "OpenAI 兼容",
    baseUrl: "https://api.moonshot.cn/v1", recommendedModel: "kimi-k2",
    models: ["kimi-k2", "kimi-k2-0905-preview"],
    supportsTest: true, isLocal: false,
    helpUrl: "https://platform.moonshot.cn/docs",
    note: "Moonshot 开放平台，OpenAI 兼容协议。",
  },
  {
    id: "deepseek", name: "DeepSeek", kind: "deepseek", kindLabel: "DeepSeek 协议",
    baseUrl: "https://api.deepseek.com/v1", recommendedModel: "deepseek-chat",
    models: ["deepseek-chat", "deepseek-reasoner"],
    supportsTest: true, isLocal: false,
    helpUrl: "https://api-docs.deepseek.com",
    note: "高性价比国产模型，推理与对话分离。",
  },
  {
    id: "qwen", name: "通义千问 / 百炼", kind: "openai_compatible", kindLabel: "OpenAI 兼容",
    baseUrl: "https://dashscope.aliyuncs.com/compatible-mode/v1", recommendedModel: "qwen-plus",
    models: ["qwen-plus", "qwen-max", "qwen-turbo"],
    supportsTest: true, isLocal: false,
    helpUrl: "https://help.aliyun.com/zh/model-studio",
    note: "阿里云百炼 OpenAI 兼容模式。",
  },
  {
    id: "zhipu", name: "智谱 GLM", kind: "openai_compatible", kindLabel: "OpenAI 兼容",
    baseUrl: "https://open.bigmodel.cn/api/paas/v4", recommendedModel: "glm-4.5",
    models: ["glm-4.5", "glm-4.5-air", "glm-4-flash"],
    supportsTest: true, isLocal: false,
    helpUrl: "https://docs.bigmodel.cn",
    note: "智谱开放平台，原生兼容 OpenAI 格式。",
  },
  {
    id: "minimax", name: "MiniMax", kind: "openai_compatible", kindLabel: "OpenAI 兼容",
    baseUrl: "https://api.minimaxi.com/v1", recommendedModel: "MiniMax-M2",
    models: ["MiniMax-M2"],
    supportsTest: true, isLocal: false,
    helpUrl: "https://platform.minimaxi.com/document",
    note: "MiniMax 开放平台 OpenAI 兼容接口。",
  },
  {
    id: "openrouter", name: "OpenRouter", kind: "openai_compatible", kindLabel: "OpenAI 兼容",
    baseUrl: "https://openrouter.ai/api/v1", recommendedModel: "openai/gpt-4.1-mini",
    models: ["openai/gpt-4.1-mini", "anthropic/claude-sonnet-4-5", "deepseek/deepseek-chat"],
    supportsTest: true, isLocal: false,
    helpUrl: "https://openrouter.ai/docs",
    note: "聚合多家模型的统一网关，模型 ID 形如 vendor/model。",
  },
  {
    id: "ollama", name: "Ollama", kind: "openai_compatible", kindLabel: "OpenAI 兼容",
    baseUrl: "http://127.0.0.1:11434/v1", recommendedModel: "",
    models: [],
    supportsTest: true, isLocal: true,
    helpUrl: "https://ollama.com/docs",
    note: "本机 Ollama 服务；模型名以本机已拉取的为准。",
  },
  {
    id: "lmstudio", name: "LM Studio", kind: "openai_compatible", kindLabel: "OpenAI 兼容",
    baseUrl: "http://127.0.0.1:1234/v1", recommendedModel: "",
    models: [],
    supportsTest: true, isLocal: true,
    helpUrl: "https://lmstudio.ai/docs",
    note: "本机 LM Studio 本地服务器；模型名以已加载的为准。",
  },
  {
    id: "custom-openai", name: "自定义 OpenAI 兼容服务", kind: "openai_compatible", kindLabel: "OpenAI 兼容",
    baseUrl: "", recommendedModel: "",
    models: [],
    supportsTest: true, isLocal: false,
    helpUrl: "",
    note: "任意兼容 OpenAI 协议的端点，手动填写地址与模型。",
  },
  {
    id: "custom-anthropic", name: "自定义 Anthropic 兼容服务", kind: "anthropic", kindLabel: "Anthropic 兼容",
    baseUrl: "", recommendedModel: "",
    models: [],
    supportsTest: true, isLocal: false,
    helpUrl: "",
    note: "任意兼容 Anthropic 协议的端点，手动填写地址与模型。",
  },
];

export function presetById(id: string): ProviderPreset | undefined {
  return PROVIDER_PRESETS.find((preset) => preset.id === id);
}
