import { BrowserRouter, Route, Routes } from "react-router-dom";

import { ProjectsPage } from "../pages/ProjectsPage";
import { ResumePage } from "../pages/ResumePage";
import { SectionPage } from "../pages/SectionPage";
import { OpportunitiesPage } from "../pages/OpportunitiesPage";
import { TodayPage } from "../pages/TodayPage";
import { CapabilitiesPage } from "../pages/CapabilitiesPage";
import { CapabilityInboxPage } from "../pages/CapabilityInboxPage";
import { EvidencePage } from "../pages/EvidencePage";
import { HistoryPage } from "../pages/HistoryPage";
import { AppShell } from "./AppShell";
import { ErrorBoundary } from "./ErrorBoundary";
import { PluginsPage } from "../pages/PluginsPage";
import { KnowledgePage } from "../pages/KnowledgePage";

const sections = [
  ["context", "Me / Context", "个人上下文页面尚未接入，未查询个人记录。"],
  ["settings", "Settings", "偏好设置页面尚未接入，未读取本地配置。"],
] as const;

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<TodayPage />} />
            <Route path="projects" element={<ProjectsPage />} />
            <Route path="resume" element={<ResumePage />} />
            <Route path="opportunities" element={<OpportunitiesPage />} />
            <Route path="capabilities" element={<CapabilitiesPage />} />
            <Route path="capabilities/inbox" element={<CapabilityInboxPage />} />
            <Route path="history" element={<HistoryPage />} />
            <Route path="history/evidence" element={<EvidencePage />} />
            <Route path="plugins" element={<PluginsPage />} />
            <Route path="knowledge" element={<KnowledgePage />} />
            {sections.map(([path, title, emptyLabel]) => (
              <Route
                key={path}
                path={path}
                element={<SectionPage title={title} emptyLabel={emptyLabel} />}
              />
            ))}
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
