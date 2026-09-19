import { CirclePlus, Search } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

import { navigation } from "./navigation";

export function AppShell() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand" aria-label="Agent Career Harness">
          <img className="brand-mark" src="/brand-icon.png" alt="" />
          <span className="brand-copy">
            <strong>观复</strong>
            <small>CAREER HARNESS</small>
          </span>
        </div>
        <p className="brand-motto">看见经历<br />也看见自己</p>
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
          职业是一段长途
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
