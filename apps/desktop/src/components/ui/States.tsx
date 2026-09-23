import { AlertCircle, Inbox, RotateCcw, type LucideIcon } from "lucide-react";
import { type ReactNode } from "react";

export function Spinner({ label }: { label?: string }) {
  return (
    <span role={label ? "status" : undefined} aria-label={label}>
      <span className="spinner" aria-hidden={label ? true : undefined} />
    </span>
  );
}

export function LoadingState({ label, compact }: { label: string; compact?: boolean }) {
  return (
    <div className={compact ? "state state--compact" : "state"} role="status" aria-live="polite">
      <span className="spinner" aria-hidden="true" />
      <p>{label}</p>
    </div>
  );
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="skeleton" aria-hidden="true">
      {Array.from({ length: rows }, (_, index) => (
        <span
          key={index}
          className={`skeleton__row ${index % 3 === 1 ? "skeleton__row--short" : index % 3 === 2 ? "skeleton__row--mid" : ""}`}
        />
      ))}
    </div>
  );
}

interface EmptyStateProps {
  title: string;
  description?: ReactNode;
  icon?: LucideIcon;
  action?: ReactNode;
  compact?: boolean;
}

export function EmptyState({ title, description, icon: Icon = Inbox, action, compact }: EmptyStateProps) {
  return (
    <div className={compact ? "state state--compact" : "state"}>
      <span className="state__icon" aria-hidden="true"><Icon size={19} /></span>
      <h3>{title}</h3>
      {description ? <p>{description}</p> : null}
      {action ? <div className="state__actions">{action}</div> : null}
    </div>
  );
}

interface ErrorStateProps {
  title: string;
  description?: ReactNode;
  /** 原始技术信息，仅显示在折叠的“查看诊断”里。 */
  detail?: string;
  onRetry?: () => void;
  retryLabel?: string;
  compact?: boolean;
}

/** 统一错误/离线状态：中文主文案 + 恢复操作 + 折叠技术详情。 */
export function ErrorState({ title, description, detail, onRetry, retryLabel = "重试", compact }: ErrorStateProps) {
  return (
    <div className={compact ? "state state--compact" : "state"} role="alert">
      <span className="state__icon state__icon--danger" aria-hidden="true"><AlertCircle size={19} /></span>
      <h3>{title}</h3>
      {description ? <p>{description}</p> : null}
      {onRetry ? (
        <div className="state__actions">
          <button type="button" className="btn btn--secondary" onClick={onRetry}>
            <RotateCcw size={15} aria-hidden="true" />
            <span>{retryLabel}</span>
          </button>
        </div>
      ) : null}
      {detail ? (
        <details className="state__details">
          <summary>查看诊断</summary>
          <pre>{detail}</pre>
        </details>
      ) : null}
    </div>
  );
}
