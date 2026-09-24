import { type ReactNode } from "react";

import { SunriseArt } from "./SunriseArt";

interface PageHeaderProps {
  eyebrow: string;
  title: string;
  description?: string;
  actions?: ReactNode;
  /** 头部右侧的轻量日出点缀（仅部分主页面使用）。 */
  art?: boolean;
}

/** 统一页面头：眉题 → 标题 + 一句说明 → 页面级操作。 */
export function PageHeader({ eyebrow, title, description, actions, art }: PageHeaderProps) {
  return (
    <header className="page-heading">
      <div className="page-heading__text">
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        {description ? <p className="page-heading__desc">{description}</p> : null}
      </div>
      {actions ? <div className="page-heading__actions">{actions}</div> : null}
      {art ? <SunriseArt /> : null}
    </header>
  );
}
