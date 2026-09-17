import { CirclePlus, Search } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { navigation } from "./navigation";

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand" aria-label="Agent Career Harness">
          <span className="brand-mark">ACH</span>
          <span className="brand-copy">
            <strong>Career Harness</strong>
            <small>Local workspace</small>
          </span>
        </div>
        <nav className="primary-nav" aria-label="Primary navigation">
          {navigation.map(({ path, label, icon: Icon }) => (
            <NavLink key={path} to={path} end={path === "/"}>
              <Icon size={18} aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <span className="privacy-dot" aria-hidden="true" />
          Local-first
        </div>
      </aside>

      <div className="workspace">
        <header className="topbar">
          <label className="search-field">
            <Search size={17} aria-hidden="true" />
            <span className="sr-only">Search workspace</span>
            <input type="search" placeholder="Search workspace" disabled />
          </label>
          <button className="capture-button" type="button" disabled>
            <CirclePlus size={18} aria-hidden="true" />
            <span>Capture</span>
          </button>
        </header>
        <div className="content-scroll">
          <Outlet />
        </div>
      </div>
    </div>
  );
}
