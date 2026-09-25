import { type LucideIcon } from "lucide-react";
import { useId, type ReactNode } from "react";

interface SurfaceProps {
  children: ReactNode;
  className?: string;
  ariaLabel?: string;
}

/** 页面主工作表面：一个页面尽量只有一张。 */
export function Surface({ children, className, ariaLabel }: SurfaceProps) {
  return (
    <div className={["surface", className ?? ""].filter(Boolean).join(" ")} aria-label={ariaLabel}>
      {children}
    </div>
  );
}

interface SectionProps {
  title: ReactNode;
  description?: ReactNode;
  meta?: ReactNode;
  icon?: LucideIcon;
  children: ReactNode;
  className?: string;
  ariaLabel?: string;
}

/** 主工作表面内的分区：图标（可选）+ 标题 + 说明 + 内容，分区之间发丝线分隔。 */
export function Section({ title, description, meta, icon: Icon, children, className, ariaLabel }: SectionProps) {
  const titleId = useId();
  return (
    <section
      className={["section", className ?? ""].filter(Boolean).join(" ")}
      aria-labelledby={ariaLabel ? undefined : titleId}
      aria-label={ariaLabel}
    >
      <div className="section__heading">
        <div className="section__title">
          <h2 id={titleId}>
            {Icon ? (
              <span className="section__icon" aria-hidden="true"><Icon size={17} /></span>
            ) : null}
            {title}
          </h2>
          {description ? <p>{description}</p> : null}
        </div>
        {meta ? <span className="section__meta">{meta}</span> : null}
      </div>
      {children}
    </section>
  );
}
