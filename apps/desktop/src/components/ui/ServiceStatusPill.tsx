import { RotateCcw } from "lucide-react";

import { useHealth } from "../../api/useHealth";

interface ServiceStatusPillProps {
  /** sidebar 显示完整文案；toolbar 只显示紧凑状态。 */
  variant?: "sidebar" | "toolbar";
}

/** 侧栏与工具栏共用的本地服务状态入口。 */
export function ServiceStatusPill({ variant = "sidebar" }: ServiceStatusPillProps) {
  const [health, retry] = useHealth();
  const label = health.status === "online"
    ? (variant === "sidebar" ? `本地服务已连接 · ${health.data.version}` : "已连接")
    : health.status === "loading"
      ? "正在连接本地服务"
      : "本地服务离线";
  return (
    <span
      className={`service-pill service-pill--${health.status}`}
      role="status"
      aria-live="polite"
      title={health.status === "offline" ? health.message : label}
    >
      <span className="service-pill__dot" aria-hidden="true" />
      <span className="service-pill__text">{label}</span>
      {health.status === "offline" ? (
        <button type="button" onClick={retry} title="重试连接" aria-label="重试连接本地服务">
          <RotateCcw size={13} aria-hidden="true" />
        </button>
      ) : null}
    </span>
  );
}
