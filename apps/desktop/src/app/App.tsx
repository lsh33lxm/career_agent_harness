import { BrowserRouter, Route, Routes } from "react-router-dom";

import { ProjectsPage } from "../pages/ProjectsPage";
import { ResumePage } from "../pages/ResumePage";
import { SettingsPage } from "../pages/SettingsPage";
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
import { ContextPage } from "../pages/ContextPage";
import { AIWorkbenchPage } from "../pages/AIWorkbenchPage";
import { CommunicationMailboxPage } from "../pages/CommunicationMailboxPage";
import { ApplicationsPage } from "../pages/ApplicationsPage";

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
            <Route path="context" element={<ContextPage />} />
            <Route path="ai-workbench" element={<AIWorkbenchPage />} />
            <Route path="communications" element={<CommunicationMailboxPage />} />
            <Route path="applications" element={<ApplicationsPage />} />
            <Route path="settings" element={<SettingsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
