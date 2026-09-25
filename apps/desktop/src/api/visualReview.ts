import { ApiError } from "./client";

/**
 * 视觉验收 fixture 模式 —— 仅开发环境可用。
 * 启用方式：`npm run dev` 后访问 `http://127.0.0.1:<port>/?demo=visual-review`，
 * 或设置 `VITE_VISUAL_REVIEW=true` / `window.__ACH_CONFIG__.visualReview = true`。
 * 生产构建中 `import.meta.env.DEV` 为 false，该分支会被静态移除，绝不注入假数据。
 */
export function isVisualReviewMode(): boolean {
  if (!import.meta.env.DEV) return false;
  return (
    window.__ACH_CONFIG__?.visualReview === true
    || import.meta.env.VITE_VISUAL_REVIEW === "true"
    || window.location.search.includes("demo=visual-review")
  );
}

/** 仅视觉验收模式调用：按路径返回 fixture；未覆盖的 GET 返回空数组，写操作返回空对象。 */
export async function visualReviewRequest(path: string, init: RequestInit): Promise<unknown> {
  const {
    fixtures, fixtureJobs, fixtureJobDetail, fixtureProjects, fixtureProjectDetail,
    fixtureAnalyses, fixtureCapabilities, fixtureResumeBase, fixtureResumeRevisions,
    fixtureResumeBaseHistory, fixtureApplications, fixtureOutcomes, fixtureInterviews,
    fixtureMemories, fixtureMemoryProposals, fixtureEvidencePage, fixtureWikiHealth,
    fixtureKnowledgeSearch, fixtureConnectors, fixtureSyncRuns, fixtureModelProviders,
    fixtureTasks, fixturePlugins,
  } = await import("./visualReviewFixtures");

  const method = (init.method ?? "GET").toUpperCase();
  const clean = path.split("?")[0].replace(/\/+$/, "");

  if (method === "GET") {
    if (clean in fixtures) return fixtures[clean];
    if (clean === "/api/v1/legacy/jobs") return fixtureJobs;
    if (clean.startsWith("/api/v1/legacy/jobs/")) return fixtureJobDetail;
    if (clean === "/api/v1/projects") return fixtureProjects;
    if (/^\/api\/v1\/projects\/[^/]+$/.test(clean)) return fixtureProjectDetail;
    if (/^\/api\/v1\/github\/projects\/[^/]+\/analyses$/.test(clean)) return fixtureAnalyses;
    if (clean === "/api/v1/capabilities/identities") return ["candidate_001"];
    if (/^\/api\/v1\/capabilities\/[^/]+$/.test(clean)) return fixtureCapabilities;
    if (clean === "/api/v1/capability-inbox") return [];
    if (clean === "/api/v1/resumes") return [fixtureResumeBase];
    if (/^\/api\/v1\/resumes\/[^/]+\/base$/.test(clean)) return fixtureResumeBase;
    if (/^\/api\/v1\/resumes\/[^/]+\/revisions$/.test(clean)) return fixtureResumeRevisions;
    if (/^\/api\/v1\/resumes\/[^/]+\/bases$/.test(clean)) return fixtureResumeBaseHistory;
    if (clean === "/api/v1/applications") return fixtureApplications;
    const outcomeMatch = /^\/api\/v1\/applications\/([^/]+)\/outcomes$/.exec(clean);
    if (outcomeMatch) return fixtureOutcomes[outcomeMatch[1]] ?? [];
    const interviewMatch = /^\/api\/v1\/applications\/([^/]+)\/interviews$/.exec(clean);
    if (interviewMatch) return fixtureInterviews[interviewMatch[1]] ?? [];
    if (clean === "/api/v1/memory") return fixtureMemories;
    if (clean === "/api/v1/memory/proposals") return fixtureMemoryProposals;
    if (clean === "/api/v1/evidence") return fixtureEvidencePage;
    const evidenceMatch = /^\/api\/v1\/evidence\/([^/]+)$/.exec(clean);
    if (evidenceMatch) {
      const found = (fixtureEvidencePage.items as Array<{ evidence_ref: { evidence_ref_id: string } }>)
        .find((item) => item.evidence_ref.evidence_ref_id === decodeURIComponent(evidenceMatch[1]));
      if (!found) throw new ApiError("这条证据引用不存在。", 404);
      return found;
    }
    if (clean === "/api/v1/wiki/health") return fixtureWikiHealth;
    if (clean === "/api/v1/source-connectors") return fixtureConnectors;
    const syncMatch = /^\/api\/v1\/source-connectors\/([^/]+)\/(?:sync-runs|runs)$/.exec(clean);
    if (syncMatch) return fixtureSyncRuns[decodeURIComponent(syncMatch[1])] ?? [];
    if (clean === "/api/v1/model-providers") return fixtureModelProviders;
    if (clean === "/api/v1/tasks") return fixtureTasks;
    if (clean === "/api/v1/plugins") return fixturePlugins;
    return [];
  }
  if (clean === "/api/v1/knowledge/search") return fixtureKnowledgeSearch;
  if (clean === "/api/v1/projections/feishu/today/preview") return fixtures["/api/v1/projections/feishu/today/preview"];
  // 写操作在验收模式中安全短路为成功回执，不持久化任何数据。
  return { ok: true, proposal_id: "visual-review", operation_id: "visual-review", test: { success: true } };
}
