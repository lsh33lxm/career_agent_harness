/* 视觉验收 fixture 数据 —— 仅 ?demo=visual-review 开发模式使用。 */

const now = "2026-09-23T08:00:00Z";

export const fixtures: Record<string, unknown> = {
  "/health": { status: "ok", service: "agent-career-harness", version: "0.3.1", environment: "visual-review" },

  /* ---------- 今天 ---------- */
  "/api/v1/today": {
    items: [
      {
        item_id: "today:opportunity_action:opportunity_001",
        kind: "opportunity_action",
        source_refs: [{ entity_id: "opportunity_001", kind: "opportunity", revision: 3 }],
        reasons: [{ code: "user_priority_high", explanation: "你将该岗位标为高优先级，且岗位 48 小时内截止投递。" }],
        user_priority: "high",
        suggested_priority: "urgent",
        deadline_at: "2026-09-25T10:00:00Z",
        interview_at: null,
      },
      {
        item_id: "today:application_step:application_002",
        kind: "application_step",
        source_refs: [{ entity_id: "application_002", kind: "application", revision: 2 }],
        reasons: [{ code: "step_due", explanation: "投递材料已就绪，等待你最终确认后提交。" }],
        user_priority: null,
        suggested_priority: "high",
        deadline_at: null,
        interview_at: null,
      },
      {
        item_id: "today:interview_prep:interview_001",
        kind: "interview_prep",
        source_refs: [{ entity_id: "interview_001", kind: "interview", revision: 1 }],
        reasons: [{ code: "interview_upcoming", explanation: "技术面试明天上午进行，建议今天完成一轮复盘准备。" }],
        user_priority: "medium",
        suggested_priority: "high",
        deadline_at: null,
        interview_at: "2026-09-24T02:00:00Z",
      },
    ],
    input_revisions: [
      { entity_id: "opportunity_001", kind: "opportunity", revision: 3 },
      { entity_id: "application_002", kind: "application", revision: 2 },
      { entity_id: "interview_001", kind: "interview", revision: 1 },
    ],
    generated_at: now,
    policy_version: "today-policy-v1",
  },
  "/api/v1/projections/feishu/today/preview": {
    schema_version: "feishu-today-preview-v1",
    mode: "dry_run",
    source_sha256: "a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2",
    generated_at: now,
    policy_version: "today-policy-v1",
    input_revisions: [],
    rows: [
      { ordinal: 1, item: { item_id: "today:opportunity_action:opportunity_001", kind: "opportunity_action" } },
      { ordinal: 2, item: { item_id: "today:interview_prep:interview_001", kind: "interview_prep" } },
    ],
  },

  /* ---------- 机会：历史岗位库 ---------- */
  "/api/v1/legacy/status": {
    configured_source_root: "D:/career/agent-radar",
    source_accessible: true,
    latest_report: {
      batch_id: "batch_2026_09_21",
      source_root: "D:/career/agent-radar",
      source_signature_before: "sig-before",
      source_signature_after: "sig-before",
      status: "completed",
      started_at: "2026-09-21T10:00:00Z",
      finished_at: "2026-09-21T10:01:00Z",
      files: [],
      totals: { read_count: 7575, new_count: 1028, duplicate_count: 684, failed_count: 0 },
      importer_version: "1.0",
    },
  },
  "/api/v1/legacy/knowledge-overview": {
    data_as_of: "2026-09-21T10:00:00Z",
    job_count: 1028,
    interview_count: 503,
    question_count: 4816,
    coding_count: 324,
    needs_review_count: 684,
    top_skills: [
      { label: "Python", count: 486 }, { label: "Go", count: 302 }, { label: "React", count: 265 },
      { label: "Kubernetes", count: 198 }, { label: "大模型应用", count: 176 }, { label: "数据分析", count: 154 },
    ],
    top_companies: [
      { label: "字节跳动", count: 96 }, { label: "腾讯", count: 84 }, { label: "阿里巴巴", count: 77 },
      { label: "美团", count: 63 }, { label: "百度", count: 52 },
    ],
    top_locations: [
      { label: "北京", count: 412 }, { label: "上海", count: 288 }, { label: "深圳", count: 201 }, { label: "杭州", count: 127 },
    ],
    questions: [
      {
        record_id: "q_001", title: "如何设计可审计的 Agent 工作流？", company: "字节跳动", role: "后端开发工程师",
        topic: "系统设计", observed_at: "2026-09-18", review_status: "historical_unconfirmed",
        source_path: "问题明细.csv", row_number: 42, source_sha256: "f".repeat(64),
      },
      {
        record_id: "q_002", title: "讲一次你用缓存解决性能瓶颈的经历", company: "腾讯", role: "后端开发工程师",
        topic: "项目深挖", observed_at: "2026-09-12", review_status: "historical_unconfirmed",
        source_path: "问题明细.csv", row_number: 87, source_sha256: "e".repeat(64),
      },
    ],
    interviews: [
      {
        record_id: "i_001", title: "技术一面", company: "字节跳动", role: "后端开发工程师",
        topic: "技术面试", observed_at: "2026-09-18", review_status: "historical_unconfirmed",
        source_path: "面试记录.csv", row_number: 12, source_sha256: "d".repeat(64),
      },
      {
        record_id: "i_002", title: "项目复盘面", company: "美团", role: "产品经理",
        topic: "项目复盘", observed_at: "2026-09-08", review_status: "needs_review",
        source_path: "面试记录.csv", row_number: 33, source_sha256: "c".repeat(64),
      },
    ],
  },

  /* ---------- 机会：求职流程与沟通草稿 ---------- */
  "/api/v1/opportunities": [
    {
      opportunity: { entity_id: "opportunity_001", revision: 3, schema_version: 1, state: "qualified" },
      job: { job_id: "job_001", revision: 2 },
      suggested_priority: {
        opportunity_id: "opportunity_001", level: "urgent",
        reasons: ["与目标岗位方向一致", "岗位 48 小时内截止"],
        input_revisions: [{ entity_id: "job_001", revision: 2 }],
        calculated_at: "2026-09-22T10:00:00Z", score: 0.91, rank: 1,
      },
      user_priority: { opportunity_id: "opportunity_001", level: "high", actor: "user", set_at: "2026-09-22T11:00:00Z", reason: "方向匹配，优先推进" },
    },
    {
      opportunity: { entity_id: "opportunity_002", revision: 1, schema_version: 1, state: "watching" },
      job: { job_id: "job_002", revision: 1 },
      suggested_priority: {
        opportunity_id: "opportunity_002", level: "medium",
        reasons: ["技能覆盖度中等", "薪资区间符合预期"],
        input_revisions: [{ entity_id: "job_002", revision: 1 }],
        calculated_at: "2026-09-21T09:00:00Z", score: 0.62, rank: 2,
      },
      user_priority: null,
    },
  ],
  "/api/v1/communications/drafts": [
    {
      draft_id: "draft_001", opportunity_id: "opportunity_001", source_staging_id: null,
      channel: "follow_up_note", recipient: null,
      body: "您好，我对后端开发工程师岗位很感兴趣，想确认一下投递材料的审核进度，并补充了最新的项目链接。",
      status: "pending_review",
      provenance: { source: "user", mode: "local" },
      reviewed_by: null, review_reason: null,
    },
    {
      draft_id: "draft_002", opportunity_id: "opportunity_002", source_staging_id: null,
      channel: "follow_up_note", recipient: null,
      body: "感谢面试安排，想确认面试的具体形式与时长，以便提前准备白板演示环境。",
      status: "approved",
      provenance: { source: "user", mode: "local" },
      reviewed_by: "user", review_reason: "用户确认草稿",
    },
  ],
  "/api/v1/communications/summary": {
    created_today: 1, daily_limit: 5, remaining_today: 4,
    reply_count: 2, follow_up_count: 1, channel_counts: { email: 1, platform_message: 1 },
  },
};

/* eslint-disable */
/* 追加：岗位 / 项目 / 能力 fixture */
export const fixtureJobs = [
  {
    staging_id: "staging_001", title: "后端开发工程师", company: "字节跳动",
    location: '["北京", "海淀区"]', salary: "25k-40k",
    source_url: "https://example.com/jobs/1", status: "staged", duplicate_of: null,
    suggested_score: 0.86, review_status: "historical_unconfirmed",
    source_path: "data/统一数据/岗位与JD数据.csv", source_class: "unified_job",
    source_sha256: "a".repeat(64), row_number: 161, imported_at: "2026-09-21T10:00:00Z",
    tags: ['["Python", "Go", "分布式系统"]'],
  },
  {
    staging_id: "staging_002", title: "算法工程师（推荐方向）", company: "阿里巴巴",
    location: '["杭州", "余杭区"]', salary: "30k-50k",
    source_url: "https://example.com/jobs/2", status: "staged", duplicate_of: null,
    suggested_score: 0.74, review_status: "historical_unconfirmed",
    source_path: "data/统一数据/岗位与JD数据.csv", source_class: "unified_job",
    source_sha256: "b".repeat(64), row_number: 205, imported_at: "2026-09-21T10:00:00Z",
    tags: ['["推荐系统", "PyTorch"]'],
  },
  {
    staging_id: "staging_003", title: "大模型应用工程师", company: "腾讯",
    location: '["深圳", "南山区"]', salary: "35k-55k",
    source_url: "https://example.com/jobs/3", status: "admitted", duplicate_of: null,
    suggested_score: 0.91, review_status: "historical_unconfirmed",
    source_path: "data/统一数据/岗位与JD数据.csv", source_class: "unified_job",
    source_sha256: "c".repeat(64), row_number: 318, imported_at: "2026-09-20T08:00:00Z",
    tags: ['["LLM", "RAG", "Prompt 工程"]'],
  },
  {
    staging_id: "staging_004", title: "数据分析师", company: "美团",
    location: '["北京", "朝阳区"]', salary: "20k-35k",
    source_url: null, status: "duplicate", duplicate_of: "staging_001",
    suggested_score: 0.52, review_status: "duplicate",
    source_path: "data/统一数据/岗位与JD数据.csv", source_class: "candidate_platform",
    source_sha256: "d".repeat(64), row_number: 402, imported_at: "2026-09-19T08:00:00Z",
    tags: ['["SQL", "Tableau"]'],
  },
  {
    staging_id: "staging_005", title: "全栈开发工程师", company: "小红书",
    location: '["上海", "徐汇区"]', salary: "28k-45k",
    source_url: "https://example.com/jobs/5", status: "staged", duplicate_of: null,
    suggested_score: 0.79, review_status: "needs_review",
    source_path: "data/统一数据/岗位与JD数据.csv", source_class: "candidate_canonical",
    source_sha256: "e".repeat(64), row_number: 512, imported_at: "2026-09-16T08:00:00Z",
    tags: ['["React", "Node.js", "TypeScript"]'],
  },
];

export const fixtureJobDetail = {
  job: fixtureJobs[0],
  jd_text: "负责 Agent Harness 平台后端开发与稳定性建设。\n\n参与任务编排、证据链与审计子系统的设计；\n与产品协作完成求职工作流的可追溯落地。\n\n要求：熟悉 Python/Go，具备分布式系统经验，有高可靠服务实践经验者优先。",
  raw_record: {},
  transform: {},
  batch_id: "batch_2026_09_21",
  related_interviews: [{ title: "技术一面", interview_date: "2026-09-18" }],
};

export const fixtureProjects = [
  { project_id: "proj_001", revision: 4, display_name: "个人博客系统", created_by: "user", created_at: "2026-03-12" },
  { project_id: "proj_002", revision: 2, display_name: "智能简历生成器", created_by: "user", created_at: "2026-01-20" },
  { project_id: "proj_003", revision: 3, display_name: "数据可视化分析平台", created_by: "user", created_at: "2025-11-02" },
  { project_id: "proj_004", revision: 1, display_name: "校园二手交易小程序", created_by: "user", created_at: "2025-06-15" },
];

export const fixtureProjectDetail = {
  project: fixtureProjects[0],
  evidence: [
    {
      evidence_id: "pe_001", summary: "Next.js 博客系统：实现文章发布、标签与全文检索",
      authority: "code_verified", review_status: "approved", freshness: "current",
      source_manifest: { entries: [{ relative_path: "README.md", sha256: "ab".repeat(32), byte_length: 4821 }] },
    },
    {
      evidence_id: "pe_002", summary: "独立完成部署与监控接入，月访问量 3k+",
      authority: "user_confirmed", review_status: "pending", freshness: "stale",
      source_manifest: { entries: [{ relative_path: "docs/deploy.md", sha256: "cd".repeat(32), byte_length: 2104 }] },
    },
  ],
};

export const fixtureAnalyses = [
  {
    analysis_id: "ana_001", project_id: "proj_001", repository_url: "https://github.com/me/personal-blog",
    commit_sha: "a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2", file_count: 86, byte_count: 1240921,
    readme_sha256: "ef".repeat(32),
    profile: {
      technology_stack: ["Next.js", "React", "TypeScript", "Tailwind CSS"],
      dependency_manifests: ["package.json"],
      tests: ["vitest", "playwright"],
      deployment: ["Vercel", "GitHub Actions"],
      recent_activity: [{ authored_at: "2026-09-10", title: "feat: add全文检索索引" }],
      outcome_clues: ["README 记录了 3k+ 月访问量"],
      risk_notes: [],
    },
    provenance: { analyzer: "github-static-v2", readme: "README.md" },
  },
];

export const fixtureCapabilities = {
  candidate_id: "candidate_001",
  graph_version: {
    graph_version_id: "graph_001", version_label: "v3", parent_graph_version_id: null,
    change_note: "", released_at: "2026-09-20T08:00:00Z", released_by: "system", released_by_kind: "rule",
  },
  nodes: [
    { capability_id: "cap_001", canonical_name: "后端工程", description: "服务设计、接口契约与稳定性建设。", layer: "common_core", lifecycle_status: "active", graph_version_id: "graph_001" },
    { capability_id: "cap_002", canonical_name: "大模型应用", description: "RAG、评测与 Agent 编排落地。", layer: "track", lifecycle_status: "active", graph_version_id: "graph_001" },
    { capability_id: "cap_003", canonical_name: "数据分析", description: "指标建模与可视化表达。", layer: "common_core", lifecycle_status: "active", graph_version_id: "graph_001" },
    { capability_id: "cap_004", canonical_name: "项目管理", description: "跨团队推进与风险管理。", layer: "common_core", lifecycle_status: "active", graph_version_id: "graph_001" },
    { capability_id: "cap_005", canonical_name: "领域业务理解", description: "招聘场景业务规则与合规边界。", layer: "opportunity_specific", lifecycle_status: "active", graph_version_id: "graph_001" },
  ],
  relations: [
    { relation_id: "rel_001", source_capability_id: "cap_002", target_capability_id: "cap_001", relation_type: "related_to", graph_version_id: "graph_001" },
  ],
  projections: [
    {
      capability_id: "cap_001",
      personal_state: {
        personal_state_id: "ps_001", candidate_id: "candidate_001", capability_id: "cap_001",
        understand: true, explain: true, apply: true, evidence: true, interview_ready: true,
        revision: 5, display_status: "verified", updated_at: "2026-09-20T08:00:00Z",
      },
      evidence_bindings: [
        { binding_id: "eb_001", evidence_ref_id: "ev_001", project_evidence_id: "pe_001", project_evidence_revision: 1, authority: "code_verified", scopes: ["项目证据"] },
      ],
      target_market_bindings: [{ binding_id: "mb_001", market_scope: "target", source_evidence_refs: ["ev_001"], opportunity_id: "opportunity_001", job_requirement_id: null }],
      broad_market_bindings: [{ binding_id: "mb_002", market_scope: "broad", source_evidence_refs: [], opportunity_id: null, job_requirement_id: "jr_001" }],
      investment_state: { investment_state_id: "is_001", recommendation: "high", score: 0.88, reasons: ["目标岗位高频要求", "已有可验证项目证据"], rule_version: "invest-v1", calculated_at: "2026-09-22T08:00:00Z" },
    },
    {
      capability_id: "cap_002",
      personal_state: {
        personal_state_id: "ps_002", candidate_id: "candidate_001", capability_id: "cap_002",
        understand: true, explain: true, apply: false, evidence: false, interview_ready: false,
        revision: 2, display_status: "practiced", updated_at: "2026-09-18T08:00:00Z",
      },
      evidence_bindings: [],
      target_market_bindings: [{ binding_id: "mb_003", market_scope: "target", source_evidence_refs: [], opportunity_id: "opportunity_001", job_requirement_id: null }],
      broad_market_bindings: [],
      investment_state: { investment_state_id: "is_002", recommendation: "high", score: 0.81, reasons: ["目标方向明确需要", "当前缺少证据支撑"], rule_version: "invest-v1", calculated_at: "2026-09-22T08:00:00Z" },
    },
    { capability_id: "cap_003", personal_state: null, evidence_bindings: [], target_market_bindings: [], broad_market_bindings: [], investment_state: null },
    {
      capability_id: "cap_004",
      personal_state: {
        personal_state_id: "ps_004", candidate_id: "candidate_001", capability_id: "cap_004",
        understand: true, explain: false, apply: true, evidence: false, interview_ready: false,
        revision: 1, display_status: "applied", updated_at: "2026-09-15T08:00:00Z",
      },
      evidence_bindings: [],
      target_market_bindings: [],
      broad_market_bindings: [{ binding_id: "mb_004", market_scope: "broad", source_evidence_refs: [], opportunity_id: null, job_requirement_id: "jr_002" }],
      investment_state: { investment_state_id: "is_004", recommendation: "medium", score: 0.55, reasons: ["通用能力，差异化有限"], rule_version: "invest-v1", calculated_at: "2026-09-22T08:00:00Z" },
    },
    { capability_id: "cap_005", personal_state: null, evidence_bindings: [], target_market_bindings: [], broad_market_bindings: [], investment_state: { investment_state_id: "is_005", recommendation: "low", score: 0.2, reasons: ["当前机会覆盖较少"], rule_version: "invest-v1", calculated_at: "2026-09-22T08:00:00Z" } },
  ],
  input_revisions: [{ kind: "graph_version", entity_id: "graph_001", revision: null }],
  workspace_version: "capability-workspace-v1",
};

/* eslint-disable */
/* 追加：简历 / 历史 / 我的 / 插件 / 任务 / 资料源 / 证据 / 知识 fixture */
export const fixtureResumeBase = {
  resume_id: "resume_001", candidate_id: "candidate_001", revision: 3,
  sections: {
    summary: "5 年后端与大模型应用经验，主导过任务编排与证据链系统设计；偏好本地优先、可审计的产品方向。",
    experience: "2021.03–至今  某科技公司 · 高级后端工程师\n负责核心交易平台后端，QPS 提升 3 倍，主导审计子系统落地。",
    projects: "个人博客系统（Next.js 全栈，月访问 3k+）；智能简历生成器（LLM 编排）。",
    skills: "Python / Go / TypeScript / Kubernetes / LLM 应用开发",
  },
  created_by: "user", created_at: "2026-09-01",
};

export const fixtureResumeRevisions = [
  {
    revision_id: "rr_002", resume_id: "resume_001", base_revision: 3,
    content: {
      summary: "5 年后端与大模型应用经验，主导任务编排与证据链系统设计；面向平台工程岗位优化表达。",
      experience: "2021.03–至今  某科技公司 · 高级后端工程师\n负责核心交易平台后端，QPS 提升 3 倍。",
      projects: "个人博客系统（Next.js 全栈）。",
      skills: "Python / Go / TypeScript / Kubernetes",
    },
    content_sha256: "b".repeat(64),
    accepted_patch_refs: [{ entity_id: "patch_1", revision: 4 }],
    created_by: "user", created_at: "2026-09-20",
  },
  {
    revision_id: "rr_001", resume_id: "resume_001", base_revision: 2,
    content: { summary: "4 年后端经验……" },
    content_sha256: "a".repeat(64),
    accepted_patch_refs: [],
    created_by: "user", created_at: "2026-09-10",
  },
];

export const fixtureResumeBaseHistory = [
  fixtureResumeBase,
  { ...fixtureResumeBase, revision: 2, created_at: "2026-08-20", sections: { summary: "4 年后端经验……" } },
];

export const fixtureApplications = [
  { entity_id: "application_001", revision: 4, opportunity_id: "opportunity_001", opportunity_revision: 3, state: "interview", resume_revision_id: "rr_002", submission_authority: "user_confirmed", submission_evidence_ref_id: "ev_001", submitted_at: "2026-09-20T10:00:00Z" },
  { entity_id: "application_002", revision: 2, opportunity_id: "opportunity_002", opportunity_revision: 1, state: "submitted_by_user", resume_revision_id: "rr_002", submission_authority: "user_confirmed", submission_evidence_ref_id: null, submitted_at: "2026-09-15T09:00:00Z" },
  { entity_id: "application_003", revision: 3, opportunity_id: "opportunity_003", opportunity_revision: 2, state: "offer", resume_revision_id: "rr_001", submission_authority: "portal_receipt", submission_evidence_ref_id: "ev_002", submitted_at: "2026-08-28T09:00:00Z" },
  { entity_id: "application_004", revision: 2, opportunity_id: "opportunity_004", opportunity_revision: 1, state: "rejected", resume_revision_id: "rr_001", submission_authority: "user_confirmed", submission_evidence_ref_id: null, submitted_at: "2026-08-12T09:00:00Z" },
];

export const fixtureOutcomes: Record<string, unknown[]> = {
  application_001: [],
  application_002: [],
  application_003: [
    {
      entity_id: "outcome_001", revision: 1, application_id: "application_003", application_revision: 3,
      result: "offer", occurred_at: "2026-09-05T10:00:00Z", authority: "user_confirmed",
      evidence_refs: ["ev_002"], recorded_by: "user",
    },
  ],
  application_004: [
    {
      entity_id: "outcome_002", revision: 1, application_id: "application_004", application_revision: 2,
      result: "rejection", occurred_at: "2026-08-20T10:00:00Z", authority: "portal_receipt",
      evidence_refs: [], recorded_by: "user",
    },
  ],
};

export const fixtureInterviews: Record<string, unknown[]> = {
  application_001: [
    { entity_id: "interview_001", revision: 1, application_id: "application_001", application_revision: 4, round: "technical", scheduled_at: "2026-09-24T02:00:00Z", status: "scheduled", evidence_refs: ["ev_001"] },
    { entity_id: "interview_002", revision: 1, application_id: "application_001", application_revision: 4, round: "screen", scheduled_at: "2026-09-19T02:00:00Z", status: "completed", evidence_refs: ["ev_003"] },
  ],
  application_002: [],
  application_003: [],
  application_004: [],
};

export const fixtureMemories = [
  { relevance: 1, memory: { memory_id: "memory_1", revision: 3, memory_type: "preference", scope_kind: "user", scope_id: "local-user", status: "confirmed", content: "偏好本地优先、证据充分的 AI 工程岗位", source_type: "manual", source_locator: "manual://context", source_refs: [], confidence: 0.95, created_by: "user", confirmed_by: "user", created_at: "2026-09-01T08:00:00Z" } },
  { relevance: 1, memory: { memory_id: "memory_2", revision: 1, memory_type: "profile", scope_kind: "user", scope_id: "local-user", status: "confirmed", content: "5 年后端与大模型应用经验，目前在一家 AI 创业公司担任高级工程师", source_type: "manual", source_locator: "manual://context", source_refs: [], confidence: 1, created_by: "user", confirmed_by: "user", created_at: "2026-08-20T08:00:00Z" } },
  { relevance: 1, memory: { memory_id: "memory_3", revision: 2, memory_type: "interest", scope_kind: "user", scope_id: "local-user", status: "confirmed", content: "对 AI + 教育方向很感兴趣，希望长期深耕", source_type: "manual", source_locator: "manual://context", source_refs: [], confidence: 0.9, created_by: "user", confirmed_by: "user", created_at: "2026-08-12T08:00:00Z" } },
];

export const fixtureMemoryProposals = [
  { proposal_id: "mp_001", memory_type: "task", content: "本周完成字节跳动后端岗位投递并准备技术一面", source_locator: "agent://today", confidence: 0.7, created_by: "agent:today", status: "pending" },
  { proposal_id: "mp_002", memory_type: "preference", content: "期望远程或混合办公，暂不考虑完全驻场岗位", source_locator: "agent://import", confidence: 0.6, created_by: "agent:import", status: "pending" },
  { proposal_id: "mp_003", memory_type: "fact", content: "曾主导审计子系统从零到一落地，可作为 STAR 故事素材", source_locator: "agent://interview", confidence: 0.8, created_by: "agent:interview", status: "pending" },
];

export const fixtureEvidencePage = {
  items: [
    {
      evidence_ref: { evidence_ref_id: "ev_001", selector: "README.md#L1-L40" },
      source: { source_type: "github_readonly", source_id: "https://github.com/me/personal-blog", locator: "file:///cache/github/personal-blog" },
      snapshot: { snapshot_id: "snap_001", captured_at: "2026-09-10T08:00:00Z" },
      artifact: { artifact_id: "art_001", sha256: "ab".repeat(32), byte_length: 4821, artifact_class: "document", media_type: "text/markdown" },
    },
    {
      evidence_ref: { evidence_ref_id: "ev_002", selector: null },
      source: { source_type: "user_confirmed", source_id: "manual://offer-letter", locator: "用户手动确认" },
      snapshot: { snapshot_id: "snap_002", captured_at: "2026-09-05T10:00:00Z" },
      artifact: { artifact_id: "art_002", sha256: "cd".repeat(32), byte_length: 1024, artifact_class: "note", media_type: "text/plain" },
    },
    {
      evidence_ref: { evidence_ref_id: "ev_003", selector: null },
      source: { source_type: "legacy_historical_unconfirmed", source_id: "legacy://interview-001", locator: "file:///historical-origin" },
      snapshot: { snapshot_id: "snap_003", captured_at: "2026-09-18T08:00:00Z" },
      artifact: { artifact_id: "art_003", sha256: "ef".repeat(32), byte_length: 20480, artifact_class: "interview_record", media_type: "application/pdf" },
    },
  ],
  next_cursor: null,
};

export const fixtureWikiHealth = {
  score: 95, page_count: 12, link_count: 18,
  issues: [
    { issue_id: "wi_1", kind: "orphan_page", severity: "info", page_id: "page_001", message: "存在 1 个孤立页面" },
  ],
};

export const fixtureKnowledgeSearch = {
  items: [
    {
      knowledge_id: "kn_001", revision: 3, category: "interview_story", status: "approved",
      title: "产品经理面试高频问题", snippet: "整理了产品经理岗位的高频面试题及参考答案，涵盖产品思维、数据分析、项目管理等方向……",
      citation: { evidence_refs: ["ev_003"] },
    },
    {
      knowledge_id: "kn_002", revision: 1, category: "market_signal", status: "approved",
      title: "大模型产品发展趋势分析", snippet: "从技术演进、商业化落地和行业格局三个维度，分析大模型产品的发展趋势与机会……",
      citation: { evidence_refs: ["ev_001"] },
    },
    {
      knowledge_id: "kn_003", revision: 2, category: "skill", status: "approved",
      title: "AI 产品经理能力模型", snippet: "梳理 AI 产品经理所需的核心能力与成长路径，包含能力雷达图和学习资源清单……",
      citation: { evidence_refs: [] },
    },
  ],
  message: null,
  next_cursor: null,
};

export const fixtureConnectors = [
  {
    connector_id: "conn_001", connector_type: "local_folder", display_name: "我的求职资料", status: "active",
    config: { root_path: "D:\\求职资料" },
    created_at: "2026-09-01T08:00:00Z", compatibility: "ok",
  },
  {
    connector_id: "conn_002", connector_type: "github", display_name: "开源项目仓库", status: "active",
    config: { repository_url: "https://github.com/me/personal-blog" },
    created_at: "2026-09-02T08:00:00Z", compatibility: "ok",
  },
  {
    connector_id: "conn_003", connector_type: "legacy_agent_radar", display_name: "Legacy 历史数据", status: "paused",
    config: { root_path: "D:/career/agent-radar" },
    created_at: "2026-09-10T08:00:00Z", compatibility: "ok",
  },
];

export const fixtureSyncRuns: Record<string, unknown[]> = {
  conn_001: [{ run_id: "run_001", connector_id: "conn_001", status: "completed", started_at: "2026-09-22T08:00:00Z", finished_at: "2026-09-22T08:01:12Z", stats: { created: 2, updated: 5, skipped: 10, deleted: 0 } }],
  conn_002: [{ run_id: "run_002", connector_id: "conn_002", status: "completed", started_at: "2026-09-21T08:00:00Z", finished_at: "2026-09-21T08:00:40Z", stats: { created: 1, updated: 0, skipped: 8, deleted: 0 } }],
  conn_003: [],
};

export const fixtureModelProviders = [
  {
    provider_id: "openai", provider_kind: "openai", base_url: "https://api.openai.com/v1",
    default_model: "gpt-4.1-mini", timeout_seconds: 30, has_api_key: true, masked_api_key: "••••••••",
    connection_status: "connected", last_checked_at: "2026-09-22T08:00:00Z", last_error_code: null, revision: 2,
  },
  {
    provider_id: "deepseek", provider_kind: "deepseek", base_url: "https://api.deepseek.com/v1",
    default_model: "deepseek-chat", timeout_seconds: 30, has_api_key: true, masked_api_key: "••••••••",
    connection_status: "not_tested", last_checked_at: null, last_error_code: null, revision: 1,
  },
];

export const fixtureTasks = [
  { task_id: "task_001", task_type: "source.local_folder_sync", stage: "source_sync", status: "completed", progress: 1, current_attempt: 1, max_attempts: 3, last_error: null, updated_at: "2026-09-22T08:01:12Z" },
  { task_id: "task_002", task_type: "source.github_sync", stage: "source_sync", status: "processing", progress: 0.6, current_attempt: 1, max_attempts: 3, last_error: null, updated_at: "2026-09-23T07:30:00Z" },
  { task_id: "task_003", task_type: "local.health_check", stage: "maintenance", status: "failed", progress: 0.2, current_attempt: 3, max_attempts: 3, last_error: "网络连接超时", updated_at: "2026-09-23T06:00:00Z" },
];

/* eslint-disable */
/* 追加：插件目录 fixture */
export const fixturePlugins = [
  {
    manifest: {
      id: "echo-fixture", name: "Echo Fixture", version: "1.0.0", api_version: "1",
      type: "worker_plugin",
      source: { repo: "builtin://echo-fixture", ref: "v1", commit: "builtin-echo-v1", license: "Apache-2.0" },
      capabilities: ["fixture.echo", "health"],
      permissions: { network: [], filesystem: [], secrets: [], external_write: false, scope: ["read_models"] },
      data_contracts: ["PluginEnvelope"], healthcheck: { command: "health", timeout_ms: 5000 },
      replacement: { compatible_capabilities: ["fixture.echo"] }, dependencies: [],
      core_compatibility: { min_version: "0.1.0", max_version: "0.x" }, config_schema: {},
      data_migration_version: 0, cost_limits: { max_runtime_ms: 5000, max_output_bytes: 1000000 },
      security_url: "about:blank", terms_url: "about:blank",
      user_visible_description: "用于验证工具协议的确定性离线检查工具。",
    },
    installed: true,
    installation: { status: "enabled", enabled: true, current_version: "1.0.0", config: { update_policy: "notify" }, last_health_status: "ok" },
    release_scan: {
      overall: "passed",
      license: { status: "verified", spdx: "Apache-2.0", repository: "builtin://echo-fixture", ref: "v1", commit: "builtin-echo-v1", notice_requirement: "not_applicable", manual_review_status: "not_required" },
      dependencies: { status: "verified", scan_mode: "declared_license_only" },
      security: { status: "offline_pass", network_access: "none" },
    },
  },
  {
    manifest: {
      id: "career-kb-local", name: "career-kb-local", version: "0.4.2", api_version: "1",
      type: "knowledge_plugin",
      source: { repo: "builtin://career-kb-local", ref: "v0.4.2", commit: "builtin-kb-v042", license: "Apache-2.0" },
      capabilities: ["knowledge.search", "knowledge.read", "knowledge.list"],
      permissions: { network: [], filesystem: ["read:workspace"], secrets: [], external_write: false, scope: ["read_models"] },
      data_contracts: ["PluginEnvelope"], healthcheck: { command: "health", timeout_ms: 5000 },
      replacement: { compatible_capabilities: ["knowledge.search"] }, dependencies: [],
      core_compatibility: { min_version: "0.1.0", max_version: "0.x" }, config_schema: {},
      data_migration_version: 0, cost_limits: { max_runtime_ms: 8000, max_output_bytes: 2000000 },
      security_url: "about:blank", terms_url: "about:blank",
      user_visible_description: "只读访问本地职业知识；不会改写 Career Core 的权威数据。",
    },
    installed: true,
    installation: { status: "enabled", enabled: true, current_version: "0.4.2", config: { update_policy: "manual" }, last_health_status: "ok" },
    release_scan: {
      overall: "passed",
      license: { status: "verified", spdx: "Apache-2.0", repository: "builtin://career-kb-local", ref: "v0.4.2", commit: "builtin-kb-v042", notice_requirement: "not_applicable", manual_review_status: "not_required" },
      dependencies: { status: "verified", scan_mode: "declared_license_only" },
      security: { status: "offline_pass", network_access: "none" },
    },
  },
  {
    manifest: {
      id: "career-kb-weknora", name: "career-kb-weknora", version: "0.2.0", api_version: "1",
      type: "knowledge_plugin",
      source: { repo: "vendor://weknora", ref: "v0.2.0", commit: "weknora-v020", license: "MIT" },
      capabilities: ["knowledge.search", "knowledge.ask"],
      permissions: { network: ["https://*.weknora.example"], filesystem: [], secrets: ["weknora_api_key"], external_write: false, scope: ["read_models"] },
      data_contracts: ["PluginEnvelope"], healthcheck: { command: "health", timeout_ms: 8000 },
      replacement: { compatible_capabilities: ["knowledge.search"] }, dependencies: [],
      core_compatibility: { min_version: "0.1.0", max_version: "0.x" }, config_schema: {},
      data_migration_version: 0, cost_limits: { max_runtime_ms: 8000, max_output_bytes: 2000000 },
      security_url: "about:blank", terms_url: "about:blank",
      user_visible_description: "只读访问 WeKnora；配置服务地址、凭据并确认使用条款后才可启用。",
    },
    installed: false,
    installation: null,
    release_scan: {
      overall: "passed",
      license: { status: "verified", spdx: "MIT", repository: "vendor://weknora", ref: "v0.2.0", commit: "weknora-v020", notice_requirement: "not_applicable", manual_review_status: "not_required" },
      dependencies: { status: "verified", scan_mode: "declared_license_only" },
      security: { status: "offline_review_required", network_access: "vendor_api" },
    },
  },
];
