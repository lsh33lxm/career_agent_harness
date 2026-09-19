import type { TodayViewModel } from "./types";

// Development sample only. The production Today page renders the Core
// `GET /today` projection (contract 0.8.0) and never uses this fallback.
export function getTodayFallback(): TodayViewModel {
  return {
    dateLabel: "2026年9月20日  星期日",
    focus: {
      title: "完善 Agent Engineer 的简历版本",
      description: "这项工作连接高优先级机会与已验证项目证据，完成后进入人工审阅。",
      actionLabel: "继续完善",
      evidenceLabel: "查看依据",
    },
    opportunities: [
      { id: "byte", company: "字节跳动", role: "Agent Engineer", location: "北京", source: "BOSS直聘", matchPercent: 86, suggestedPriority: "urgent", userPriority: "high", reason: "方向一致且证据覆盖较好，截止时间临近。" },
      { id: "ali", company: "阿里巴巴", role: "AI Infra Engineer", location: "杭州", source: "官方招聘", matchPercent: 78, suggestedPriority: "high", userPriority: "high", reason: "工程背景匹配，Observability 是主要补强点。" },
      { id: "huawei", company: "华为", role: "AI Application Engineer", location: "深圳", source: "猎聘", matchPercent: 72, suggestedPriority: "medium", userPriority: "medium", reason: "应用层项目匹配，长期迁移价值仍需验证。" },
    ],
    confirmations: [
      { id: "job", title: "从网页提取的职位信息", subtitle: "字节跳动 · Agent Engineer", source: "BOSS直聘", date: "2026.09.20", description: "岗位职责与技能关键词已提取，确认后才会加入 Opportunity。", actionLabel: "确认保存" },
      { id: "fact", title: "从 PDF 提取的工作经历", subtitle: "AI 工程实习经历", source: "简历.pdf", date: "2026.09.19", description: "识别出 3 段候选经历，确认后才会进入 Career Fact。", actionLabel: "确认添加" },
    ],
    weeklySteps: [
      { label: "收集机会", date: "09.16", state: "done" },
      { label: "更新简历", date: "09.18", state: "done" },
      { label: "审阅 2 个机会", date: "09.20", state: "current" },
      { label: "准备面试", date: "09.22", state: "upcoming" },
    ],
    completedSteps: 3,
  };
}
