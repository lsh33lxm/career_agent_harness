import { BrowserRouter, Route, Routes } from "react-router-dom";

import { SectionPage } from "../pages/SectionPage";
import { OpportunitiesPage } from "../pages/OpportunitiesPage";
import { TodayPage } from "../pages/TodayPage";
import { CapabilitiesPage } from "../pages/CapabilitiesPage";
import { AppShell } from "./AppShell";
import { ErrorBoundary } from "./ErrorBoundary";

const sections = [
  ["projects", "Projects", "No connected projects"],
  ["resume", "Resume", "No resume revisions"],
  ["history", "History", "No career outcomes yet"],
  ["context", "Me / Context", "No personal context configured"],
  ["settings", "Settings", "No local preferences configured"],
] as const;

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<TodayPage />} />
            <Route path="opportunities" element={<OpportunitiesPage />} />
            <Route path="capabilities" element={<CapabilitiesPage />} />
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
