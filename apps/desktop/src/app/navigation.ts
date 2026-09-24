import {
  CircleUserRound,
  Brain,
  Mail,
  KanbanSquare,
  FolderKanban,
  FileText,
  Gauge,
  History,
  Network,
  Package,
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

export interface NavigationGroup {
  id: string;
  label: string;
  items: NavigationItem[];
}

/** 导航按任务分组；保留全部既有菜单与路由。 */
export const navigationGroups: NavigationGroup[] = [
  {
    id: "workflow",
    label: "工作流",
    items: [
      { path: "/", label: "今天", icon: Gauge },
      { path: "/opportunities", label: "机会", icon: Target },
      { path: "/projects", label: "项目", icon: FolderKanban },
      { path: "/capabilities", label: "能力", icon: Network },
    ],
  },
  {
    id: "archive",
    label: "职业档案",
    items: [
      { path: "/resume", label: "简历", icon: FileText },
      { path: "/history", label: "历史", icon: History },
      { path: "/context", label: "我的", icon: CircleUserRound },
      { path: "/ai-workbench", label: "AI 工作台", icon: Brain },
      { path: "/communications", label: "求职沟通邮箱", icon: Mail },
      { path: "/applications", label: "申请与面试", icon: KanbanSquare },
    ],
  },
  {
    id: "system",
    label: "系统与资料",
    items: [
      { path: "/knowledge", label: "知识", icon: Library },
      { path: "/plugins", label: "工具与模型", icon: Package },
      { path: "/settings", label: "设置", icon: Settings },
    ],
  },
];

export const navigation: NavigationItem[] = navigationGroups.flatMap((group) => group.items);

export function navigationLabel(pathname: string): { group: string; label: string } | null {
  for (const group of navigationGroups) {
    for (const item of group.items) {
      if (item.path === "/" ? pathname === "/" : pathname.startsWith(item.path)) {
        return { group: group.label, label: item.label };
      }
    }
  }
  return null;
}
