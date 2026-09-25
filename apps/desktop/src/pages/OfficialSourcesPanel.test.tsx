// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { admitStagedJob, listJobListingLifecycle, listJobRequirements, listJobSourcePolicies, proposeJobRequirement, reviewJobRequirement, searchOfficialJobs } from "../api/jobRadar";
import { getCapabilities, listCapabilityIdentities } from "../api/capabilities";
import { OfficialSourcesPanel } from "./OfficialSourcesPanel";

vi.mock("../api/jobRadar", () => ({
  admitStagedJob: vi.fn(),
  listJobRequirements: vi.fn(),
  proposeJobRequirement: vi.fn(),
  reviewJobRequirement: vi.fn(),
  searchOfficialJobs: vi.fn(),
  listJobListingLifecycle: vi.fn(),
  listJobSourcePolicies: vi.fn(),
}));
vi.mock("../api/capabilities", () => ({
  getCapabilities: vi.fn(),
  listCapabilityIdentities: vi.fn(),
}));

describe("OfficialSourcesPanel", () => {
  afterEach(() => cleanup());
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(listCapabilityIdentities).mockResolvedValue([]);
  });

  it("shows listing lifecycle and source failure state after a search", async () => {
    vi.mocked(searchOfficialJobs).mockResolvedValue([]);
    vi.mocked(listJobListingLifecycle).mockResolvedValue([{
      observation_id: "observation_1", source_id: "official-cn-tencent-campus", query: "AI", source_ref: "https://join.qq.com/job/1", url_fingerprint: "a".repeat(64),
      first_seen_at: "2026-09-25T08:00:00Z", last_seen_at: "2026-09-25T08:00:00Z", last_checked_at: "2026-09-25T09:00:00Z", consecutive_missing: 1, status: "pending_verification", last_success_run_id: "run_1",
    }]);
    vi.mocked(listJobSourcePolicies).mockResolvedValue([{ source_id: "official-cn-tencent-campus", rate_limit_ms: 1000, max_retries: 2, failure_threshold: 3, failure_count: 1, disabled: false, last_error: "上次响应超时", updated_at: "2026-09-25T09:00:00Z" }]);
    render(<OfficialSourcesPanel />);
    fireEvent.click(screen.getByRole("button", { name: "读取官方岗位" }));
    expect(await screen.findByText(/岗位观察：有效 0 · 待核验 1 · 已失效 0/)).toBeTruthy();
    expect(screen.getByText(/连续失败 1\/3/)).toBeTruthy();
    expect(screen.getByText(/上次响应超时/)).toBeTruthy();
  });

  it("binds an active capability before accepting a JD requirement", async () => {
    vi.mocked(listCapabilityIdentities).mockResolvedValue(["candidate_1"]);
    vi.mocked(getCapabilities).mockResolvedValue({
      candidate_id: "candidate_1",
      graph_version: { graph_version_id: "graph_1", version_label: "当前", parent_graph_version_id: null, change_note: "", released_at: "2026-09-25T00:00:00Z", released_by: "user", released_by_kind: "user" },
      nodes: [{ capability_id: "capability_python", canonical_name: "Python", description: "", layer: "common_core", lifecycle_status: "active", graph_version_id: "graph_1" }],
      relations: [], projections: [], input_revisions: [], workspace_version: "capability-workspace-v1",
    });
    vi.mocked(searchOfficialJobs).mockResolvedValue([{
      staging_id: "staging_capability", source_id: "official-cn-tencent-campus", source_ref: "https://join.qq.com/job/capability", raw_artifact_id: "artifact", raw_sha256: "a".repeat(64), url_fingerprint: "b".repeat(64), content_fingerprint: "c".repeat(64), normalized: { title: "平台工程实习生", company: "腾讯", location: "深圳", remote: null, salary: null, requirements: ["熟悉 Python"], source_url: "https://join.qq.com/job/capability" }, terms_status: "verified", status: "staged", duplicate_of: null, suggested_score: 0.5, suggested_reasons: [], gaps: [], score_breakdown: {}, admitted_job_id: null, admitted_opportunity_id: null,
    }]);
    vi.mocked(admitStagedJob).mockResolvedValue({ admission: { decision: { job: { job_id: "job_capability", revision: 1 } } } });
    vi.mocked(listJobRequirements).mockResolvedValueOnce([]).mockResolvedValueOnce([{ requirement_id: "requirement_capability_1", revision: 1, job: { job_id: "job_capability", revision: 1 }, requirement_text: "熟悉 Python", importance: "required", required_scopes: ["understand"], source_evidence_refs: ["evidence"], status: "proposed", capability_id: null, graph_version_id: null, review_reason: null, reviewed_at: null }]);
    vi.mocked(proposeJobRequirement).mockResolvedValue({ requirement: {} as never });
    vi.mocked(reviewJobRequirement).mockResolvedValue({ requirement: {} as never });

    render(<OfficialSourcesPanel />);
    fireEvent.click(screen.getByRole("button", { name: "读取官方岗位" }));
    fireEvent.click(await screen.findByRole("button", { name: "加入并审核 JD" }));
    const capability = await screen.findByRole("combobox", { name: "绑定能力 requirement_capability_1" });
    fireEvent.change(capability, { target: { value: "capability_python" } });
    fireEvent.click(screen.getByRole("button", { name: "接受" }));
    await waitFor(() => expect(reviewJobRequirement).toHaveBeenCalledWith("requirement_capability_1", 1, expect.objectContaining({ capability_id: "capability_python", graph_version_id: "graph_1" })));
  });

  it("searches a selected official source and displays staged provenance", async () => {
    vi.mocked(searchOfficialJobs).mockResolvedValue([{
      staging_id: "staging_1",
      source_id: "official-cn-tencent-campus",
      source_ref: "https://join.qq.com/job/1",
      raw_artifact_id: "artifact_1",
      raw_sha256: "a".repeat(64),
      url_fingerprint: "b".repeat(64),
      content_fingerprint: "c".repeat(64),
      normalized: { title: "AI Agent 实习生", company: "腾讯", location: "深圳", remote: null, salary: null, requirements: ["熟悉 Python"], source_url: "https://join.qq.com/job/1" },
      terms_status: "verified",
      status: "staged",
      duplicate_of: null,
      suggested_score: 0.5,
      suggested_reasons: [],
      gaps: [],
      score_breakdown: {},
      admitted_job_id: null,
      admitted_opportunity_id: null,
    }]);
    render(<OfficialSourcesPanel />);
    fireEvent.change(screen.getByLabelText("官方岗位关键词"), { target: { value: "Agent" } });
    fireEvent.click(screen.getByRole("button", { name: "读取官方岗位" }));
    await waitFor(() => expect(searchOfficialJobs).toHaveBeenCalledWith({ source_id: "official-cn-tencent-campus", query: "Agent" }));
    expect(await screen.findByText("AI Agent 实习生")).toBeTruthy();
    expect(screen.getByText("来源快照 SHA-256：aaaaaaaaaaaa…")).toBeTruthy();
  });

  it("admits a staged job and renders reviewable JD candidates", async () => {
    vi.mocked(searchOfficialJobs).mockResolvedValue([{
      staging_id: "staging_2",
      source_id: "official-cn-tencent-campus",
      source_ref: "https://join.qq.com/job/2",
      raw_artifact_id: "artifact_2",
      raw_sha256: "d".repeat(64),
      url_fingerprint: "e".repeat(64),
      content_fingerprint: "f".repeat(64),
      normalized: { title: "平台工程实习生", company: "腾讯", location: "深圳", remote: null, salary: null, requirements: ["熟悉 Python"], source_url: "https://join.qq.com/job/2" },
      terms_status: "verified",
      status: "staged",
      duplicate_of: null,
      suggested_score: 0.5,
      suggested_reasons: [],
      gaps: [],
      score_breakdown: {},
      admitted_job_id: null,
      admitted_opportunity_id: null,
    }]);
    vi.mocked(admitStagedJob).mockResolvedValue({ admission: { decision: { job: { job_id: "job_2", revision: 1 } } } });
    vi.mocked(listJobRequirements)
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([{ requirement_id: "requirement_staging_2_1", revision: 1, job: { job_id: "job_2", revision: 1 }, requirement_text: "熟悉 Python", importance: "required", required_scopes: ["understand"], source_evidence_refs: ["evidence_job_staging_x"], status: "proposed", capability_id: null, graph_version_id: null, review_reason: null, reviewed_at: null }]);
    vi.mocked(proposeJobRequirement).mockResolvedValue({ requirement: {} as never });

    render(<OfficialSourcesPanel />);
    fireEvent.click(screen.getByRole("button", { name: "读取官方岗位" }));
    fireEvent.click(await screen.findByRole("button", { name: "加入并审核 JD" }));
    expect(await screen.findByDisplayValue("熟悉 Python")).toBeTruthy();
    expect(screen.getByText(/proposed/)).toBeTruthy();
    expect(proposeJobRequirement).toHaveBeenCalledWith("job_2", 1, expect.objectContaining({ requirement_text: "熟悉 Python" }));
  });
});
