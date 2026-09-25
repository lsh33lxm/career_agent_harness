/** 厂商标识：本地渲染的品牌字母标，不依赖运行时外链图片。 */
const MARK_STYLES: Record<string, { text: string; fg: string; bg: string }> = {
  openai: { text: "OA", fg: "#ffffff", bg: "#0d3b35" },
  anthropic: { text: "AI", fg: "#ffffff", bg: "#b5502f" },
  gemini: { text: "Ge", fg: "#ffffff", bg: "#1b6a5e" },
  kimi: { text: "Ki", fg: "#ffffff", bg: "#1c1c1e" },
  deepseek: { text: "DS", fg: "#ffffff", bg: "#2b5aa6" },
  qwen: { text: "Qw", fg: "#ffffff", bg: "#5b4a9e" },
  zhipu: { text: "GLM", fg: "#ffffff", bg: "#31497e" },
  minimax: { text: "MM", fg: "#ffffff", bg: "#8f3037" },
  openrouter: { text: "OR", fg: "#ffffff", bg: "#3f3f46" },
  ollama: { text: "Ol", fg: "#17332e", bg: "#d8d2c2" },
  lmstudio: { text: "LM", fg: "#ffffff", bg: "#0e7c6b" },
};

interface ProviderMarkProps {
  presetId: string;
  size?: number;
}

export function ProviderMark({ presetId, size = 34 }: ProviderMarkProps) {
  const style = MARK_STYLES[presetId] ?? { text: "⧉", fg: "var(--green)", bg: "var(--green-soft)" };
  return (
    <span
      className="provider-mark"
      style={{
        width: size, height: size, fontSize: Math.round(size * (style.text.length > 2 ? 0.3 : 0.38)),
        color: style.fg, background: style.bg,
      }}
      aria-hidden="true"
    >
      {style.text}
    </span>
  );
}
