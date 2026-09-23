import { useEffect, useState } from "react";
import { CirclePlus, Search } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { navigation } from "./navigation";

export function AppShell() {
  const demoMode = window.__ACH_CONFIG__?.demoMode === true || import.meta.env.VITE_DEMO_MODE === "true";
  const [runtimeError, setRuntimeError] = useState(
    window.__ACH_CONFIG__?.startupError ?? window.__ACH_RUNTIME_ERROR__ ?? "",
  );
  useEffect(() => {
    const onRuntimeError = () => setRuntimeError(window.__ACH_RUNTIME_ERROR__ ?? "");
    window.addEventListener("ach-runtime-error", onRuntimeError);
    return () => window.removeEventListener("ach-runtime-error", onRuntimeError);
  }, []);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand" aria-label="观复职业工作台">
          <span className="brand-mark-frame"><img className="brand-mark" src="/brand-icon-clean.png" alt="" /></span>
          <span className="brand-copy">
            <strong>观复</strong>
            <small>CAREER HARNESS</small>
          </span>
        </div>
        <p className="brand-motto">看见经历<br />也看见自己</p>
        <nav className="primary-nav" aria-label="主导航">
          {navigation.map(({ path, label, icon: Icon }) => (
            <NavLink key={path} to={path} end={path === "/"} aria-label={label} title={label}>
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="privacy-dot" aria-hidden="true" />
          职业是一段长途
        </div>
      </aside>

      <div className="workspace">
        {demoMode && <div className="demo-banner" role="status">演示模式 · 仅展示脱敏样例，不连接真实模型或外部平台</div>}
        {runtimeError && <div className="demo-banner" role="alert">{runtimeError}</div>}
        <header className="topbar">
          <label className="search-field">
            <Search size={17} aria-hidden="true" />
            <span className="sr-only">搜索工作台</span>
            <input type="search" placeholder="搜索工作台（即将开放）" disabled />
          </label>
          <button className="capture-button" type="button" disabled>
            <CirclePlus size={18} aria-hidden="true" />
            <span>快速收集</span>
          </button>
        </header>
        <div className="content-scroll">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
