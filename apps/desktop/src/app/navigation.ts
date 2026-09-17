import {
  BarChart3,
  BriefcaseBusiness,
  CalendarClock,
  Compass,
  FileCheck2,
  FileText,
  Gauge,
  Library,
  Settings,
  Target,
  type LucideIcon,
} from "lucide-react";

export interface NavigationItem {
  path: string;
  label: string;
  icon: LucideIcon;
}

export const navigation: NavigationItem[] = [
  { path: "/", label: "Today", icon: Gauge },
  { path: "/discover", label: "Discover", icon: Compass },
  { path: "/opportunities", label: "Opportunities", icon: Target },
  { path: "/resume", label: "Resume", icon: FileText },
  { path: "/applications", label: "Applications", icon: BriefcaseBusiness },
  { path: "/interviews", label: "Interviews", icon: CalendarClock },
  { path: "/prep", label: "Prep", icon: FileCheck2 },
  { path: "/insights", label: "Insights", icon: BarChart3 },
  { path: "/evidence", label: "Evidence", icon: Library },
  { path: "/settings", label: "Settings", icon: Settings },
];
