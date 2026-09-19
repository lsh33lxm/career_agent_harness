import {
  CircleUserRound,
  FolderKanban,
  FileText,
  Gauge,
  History,
  Network,
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
  { path: "/", label: "今天", icon: Gauge },
  { path: "/opportunities", label: "机会", icon: Target },
  { path: "/projects", label: "项目", icon: FolderKanban },
  { path: "/capabilities", label: "能力", icon: Network },
  { path: "/resume", label: "简历", icon: FileText },
  { path: "/history", label: "历史", icon: History },
  { path: "/context", label: "我的", icon: CircleUserRound },
  { path: "/settings", label: "设置", icon: Settings },
];
