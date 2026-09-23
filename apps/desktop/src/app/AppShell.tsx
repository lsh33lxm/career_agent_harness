import { Bell, ChevronsLeft, ChevronsRight, CirclePlus, Menu, Search } from "lucide-react";
import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";

import { ServiceStatusPill } from "../components/ui/ServiceStatusPill";
import { navigationGroups, navigationLabel } from "./navigation";

const COLLAPSE_STORAGE_KEY = "ach.sidebar.collapsed";

export function AppShell() {
  const demoMode = window.__ACH_CONFIG__?.demoMode === true || import.meta.env.VITE_DEMO_MODE === "true";
  const location = useLocation();
  const context = navigationLabel(location.pathname);
  const [collapsed, setCollapsed] = useState(
    () => window.localStorage.getItem(COLLAPSE_STORAGE_KEY) === "1",
  );
  const [drawerOpen, setDrawerOpen] = useState(false);

  useEffect(() => {
    window.localStorage.setItem(COLLAPSE_STORAGE_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  // Route changes close the drawer and replay the page-enter transition.
  useEffect(() => {
    setDrawerOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    if (!drawerOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDrawerOpen(false);
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [drawerOpen]);

  const shellClass = [
    "app-shell",
    collapsed ? "app-shell--collapsed" : "",
    drawerOpen ? "app-shell--drawer-open" : "",
  ].filter(Boolean).join(" ");

  return (
    <div className={shellClass}>
      <div className="drawer-scrim" aria-hidden="true" onClick={() => setDrawerOpen(false)} />
      <aside className="sidebar" aria-label="应用导航">
        <div className="sidebar__brand">
          <span className="brand-mark-frame">
            <img className="brand-mark" src="/brand-icon-clean.png" alt="" />
          </span>
          <span className="brand-copy">
            <strong>观复</strong>
            <small>CAREER HARNESS</small>
          </span>
        </div>
        <p className="brand-motto">看见经历，也看见自己</p>
        <nav className="primary-nav" aria-label="主导航">
          {navigationGroups.map((group) => (
            <div className="nav-group" key={group.id}>
              <span className="nav-group__label">{group.label}</span>
              {group.items.map(({ path, label, icon: Icon }) => (
                <NavLink
                  key={path}
                  to={path}
                  end={path === "/"}
                  className="nav-item"
                  aria-label={label}
                  title={label}
                >
                  <Icon size={17} aria-hidden="true" />
                  <span>{label}</span>
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar__footer">
          <p className="sidebar__motto">职业是一段长途<br />持续积累，走向更大的可能</p>
          <ServiceStatusPill variant="sidebar" />
          <button
            type="button"
            className="sidebar__collapse"
            onClick={() => setCollapsed((value) => !value)}
            aria-label={collapsed ? "展开侧边栏" : "收起侧边栏"}
            title={collapsed ? "展开侧边栏" : "收起侧边栏"}
          >
            {collapsed
              ? <ChevronsRight size={15} aria-hidden="true" />
              : <ChevronsLeft size={15} aria-hidden="true" />}
            <span>{collapsed ? "展开" : "收起导航"}</span>
          </button>
        </div>
      </aside>

      <div className={demoMode ? "workspace workspace--demo" : "workspace"}>
        <header className="topbar">
          <button
            type="button"
            className="drawer-toggle"
            aria-label="打开导航菜单"
            aria-expanded={drawerOpen}
            onClick={() => setDrawerOpen(true)}
          >
            <Menu size={18} aria-hidden="true" />
          </button>
          <div className="topbar__context" aria-live="polite">
            {context ? (
              <>
                <small>{context.group}</small>
                <strong>{context.label}</strong>
              </>
            ) : null}
          </div>
          <div className="topbar__spacer" />
          <span className="command-entry" role="button" aria-disabled="true" title="全局搜索即将推出">
            <Search size={15} aria-hidden="true" />
            <span>搜索工作台 · 即将推出</span>
            <kbd>⌘K</kbd>
          </span>
          <span className="topbar__status">
            <ServiceStatusPill variant="toolbar" />
          </span>
          <button
            type="button"
            className="icon-btn"
            disabled
            title="通知提醒即将推出"
            aria-label="通知提醒（即将推出）"
          >
            <Bell size={16} aria-hidden="true" />
          </button>
          <span className="topbar__avatar" title="本地用户" aria-hidden="true">观</span>
          <button
            type="button"
            className="btn btn--primary"
            disabled
            title="快速收集入口即将推出"
          >
            <CirclePlus size={16} aria-hidden="true" />
            <span>快速收集</span>
          </button>
        </header>
        {demoMode ? (
          <div className="demo-banner" role="status">
            演示模式 · 仅展示脱敏样例，不连接真实模型或外部平台
          </div>
        ) : null}
        <div className="content-scroll" key={location.pathname}>
          <div className="page-enter">
            <Outlet />
          </div>
        </div>
      </div>
    </div>
  );
}
