import { BrowserRouter, Route, Routes } from "react-router-dom";

import { SectionPage } from "../pages/SectionPage";
import { TodayPage } from "../pages/TodayPage";
import { AppShell } from "./AppShell";
import { ErrorBoundary } from "./ErrorBoundary";

const sections = [
  ["discover", "Discover", "No new market observations"],
  ["opportunities", "Opportunities", "No qualified opportunities"],
  ["resume", "Resume", "No resume revisions"],
  ["applications", "Applications", "No applications in progress"],
  ["interviews", "Interviews", "No interviews scheduled"],
  ["prep", "Prep", "No preparation tasks"],
  ["insights", "Insights", "No outcome data yet"],
  ["evidence", "Evidence", "No evidence captured"],
  ["settings", "Settings", "No local preferences configured"],
] as const;

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<AppShell />}>
            <Route index element={<TodayPage />} />
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
