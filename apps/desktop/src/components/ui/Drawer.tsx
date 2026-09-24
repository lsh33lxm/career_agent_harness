import { X } from "lucide-react";
import { useEffect, useRef, type ReactNode } from "react";

interface DrawerProps {
  open: boolean;
  title: ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  ariaLabel?: string;
}

/** 右侧配置抽屉：Esc/遮罩关闭，打开时聚焦关闭按钮。 */
export function Drawer({ open, title, onClose, children, footer, ariaLabel }: DrawerProps) {
  const closeRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (!open) return;
    closeRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="drawer-root">
      <div className="drawer-root__scrim" onClick={onClose} aria-hidden="true" />
      <div className="drawer-root__panel" role="dialog" aria-modal="true" aria-label={ariaLabel}>
        <header className="drawer-root__head">
          <h2>{title}</h2>
          <button type="button" className="icon-btn" onClick={onClose} ref={closeRef} aria-label="关闭面板">
            <X size={16} aria-hidden="true" />
          </button>
        </header>
        <div className="drawer-root__body">{children}</div>
        {footer ? <footer className="drawer-root__foot">{footer}</footer> : null}
      </div>
    </div>
  );
}
