// @vitest-environment jsdom
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { searchOfficialJobs } from "../api/jobRadar";
import { OfficialSourcesPanel } from "./OfficialSourcesPanel";

vi.mock("../api/jobRadar", () => ({ searchOfficialJobs: vi.fn() }));

describe("OfficialSourcesPanel", () => {
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
});
