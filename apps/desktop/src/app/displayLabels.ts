const replaceSeparators = (value: string) => value.replaceAll("_", " ");

export const candidateStatusLabels: Record<string, string> = {
  pending: "待审核",
  accepted: "已接受",
  rejected: "已忽略",
  superseded: "已被替代",
};

export const actorLabels: Record<string, string> = {
  user: "用户",
  system: "系统",
  agent: "受控助手",
  parser: "解析器",
};

export const capabilityLayerLabels: Record<string, string> = {
  common_core: "通用核心",
  track: "方向能力",
  opportunity_specific: "机会专项",
};

export const authorityLabels: Record<string, string> = {
  user_asserted: "用户陈述",
  user_confirmed: "用户确认",
  document_supported: "材料支持",
  rule_verified: "规则验证",
  ai_inferred: "模型推断",
  portal_receipt: "门户回执",
};

export const freshnessLabels: Record<string, string> = {
  current: "当前",
  stale: "已过期",
  unknown: "未知",
};

export const reviewStatusLabels: Record<string, string> = {
  pending: "待审核",
  proposed: "待确认",
  accepted: "已接受",
  approved: "已批准",
  rejected: "已拒绝",
  historical_unconfirmed: "历史未确认",
  needs_review: "待复核",
  duplicate: "重复待复核",
};

export const artifactClassLabels: Record<string, string> = {
  public_source: "公开来源",
  personal: "个人材料",
  sensitive: "敏感材料",
  credential_session: "凭据会话",
};

export const sourceTypeLabels: Record<string, string> = {
  legacy_historical_unconfirmed: "Legacy 历史来源（未确认）",
  legacy_agent_radar: "Legacy Agent Radar",
  public_source: "公开来源",
  personal: "个人来源",
  project_scan: "项目扫描",
  github_repository: "GitHub 仓库",
};

export const taskStageLabels: Record<string, string> = {
  parsing: "解析",
  chunking: "分块",
  embedding: "向量化",
  rerank: "重排",
  graph_extraction: "图谱抽取",
  wiki_generation: "Wiki 草稿",
  memory_extraction: "记忆候选",
  source_sync: "资料源同步",
  reindex: "重新索引",
  resume_rendering: "简历渲染",
  evaluation: "评估",
  interview_preparation: "面试准备",
};

export const rendererLabels: Record<string, string> = {
  html: "HTML",
  html_css: "HTML/CSS",
  typst: "Typst",
  typst_worker: "Typst 沙箱",
};

export const atsStatusLabels: Record<string, string> = {
  passed: "通过",
  warnings: "有提醒",
  failed: "未通过",
};

export const renderStatusLabels: Record<string, string> = {
  completed: "已完成",
  failed: "失败",
  blocked: "已阻塞",
};

export const decisionLabels: Record<string, string> = {
  approved: "已批准",
  accepted: "已接受",
  rejected: "已拒绝",
  reject: "已拒绝",
};

export const syncStatusLabels: Record<string, string> = {
  processing: "同步中",
  completed: "已完成",
  failed: "失败",
};

export function displayLabel(
  value: string | null | undefined,
  labels: Record<string, string>,
  fallback = "未记录",
): string {
  if (!value) return fallback;
  return labels[value] ?? fallback;
}

export function displayTechnicalLabel(value: string | null | undefined, fallback = "未记录"): string {
  if (!value) return fallback;
  return replaceSeparators(value);
}
