import { AlertCircle, CheckCircle2, Info, type LucideIcon } from "lucide-react";
import { type ReactNode } from "react";

type BannerTone = "info" | "warning" | "danger";

const bannerIcons: Record<BannerTone, LucideIcon> = {
  info: Info,
  warning: AlertCircle,
  danger: AlertCircle,
};

interface StatusBannerProps {
  tone?: BannerTone;
  title: string;
  children?: ReactNode;
  actions?: ReactNode;
  role?: "status" | "alert";
}

/** 页面级状态条：连接不可用、演示模式等全局或分区状态。 */
export function StatusBanner({ tone = "info", title, children, actions, role }: StatusBannerProps) {
  const Icon = bannerIcons[tone];
  return (
    <div className={`banner banner--${tone}`} role={role}>
      <Icon size={16} aria-hidden="true" />
      <div className="banner__body">
        <strong>{title}</strong>
        {children ? <p>{children}</p> : null}
      </div>
      {actions ? <div className="banner__actions">{actions}</div> : null}
    </div>
  );
}

type InlineTone = "muted" | "success" | "danger";

const inlineIcons: Record<InlineTone, LucideIcon | null> = {
  muted: null,
  success: CheckCircle2,
  danger: AlertCircle,
};

interface InlineNoticeProps {
  tone?: InlineTone;
  children: ReactNode;
  role?: "status" | "alert";
}

/** 行内反馈：保存成功、表单错误、辅助说明。 */
export function InlineNotice({ tone = "muted", children, role }: InlineNoticeProps) {
  const Icon = inlineIcons[tone];
  return (
    <p className={`inline-notice inline-notice--${tone}`} role={role ?? (tone === "danger" ? "alert" : undefined)}>
      {Icon ? <Icon size={14} aria-hidden="true" /> : null}
      <span>{children}</span>
    </p>
  );
}

/** 行内错误：中文主文案 + 折叠的原始技术详情。 */
export function ErrorNotice({ label, detail }: { label: string; detail?: string }) {
  return (
    <div className="error-notice">
      <InlineNotice tone="danger" role="alert">{label}</InlineNotice>
      {detail ? (
        <details className="state__details">
          <summary>查看诊断</summary>
          <pre>{detail}</pre>
        </details>
      ) : null}
    </div>
  );
}
