// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { admitStagedJob, listJobRequirements, proposeJobRequirement, reviewJobRequirement, searchOfficialJobs } from "../api/jobRadar";
import { OfficialSourcesPanel } from "./OfficialSourcesPanel";

vi.mock("../api/jobRadar", () => ({
  admitStagedJob: vi.fn(),
  listJobRequirements: vi.fn(),
  proposeJobRequirement: vi.fn(),
  reviewJobRequirement: vi.fn(),
  searchOfficialJobs: vi.fn(),
}));

describe("OfficialSourcesPanel", () => {
  afterEach(() => cleanup());

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
