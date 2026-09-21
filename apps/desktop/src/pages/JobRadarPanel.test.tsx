// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { admitStagedJob, importManualJob, listJobStaging } from "../api/jobRadar";
import { JobRadarPanel } from "./JobRadarPanel";

vi.mock("../api/jobRadar", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/jobRadar")>();
  return { ...original, listJobStaging: vi.fn(), importManualJob: vi.fn(), admitStagedJob: vi.fn() };
});

const staged = {
  staging_id: "staging_001", source_id: "job-source-manual", source_ref: "manual://one",
  raw_artifact_id: "artifact_001", raw_sha256: "a".repeat(64), terms_status: "verified" as const,
  status: "staged" as const, duplicate_of: null, suggested_score: 0.5,
  suggested_reasons: ["matched: Python"], gaps: ["Rust"], admitted_job_id: null,
  admitted_opportunity_id: null,
  score_breakdown: { capability_match: 0.5, evidence_coverage: 0 },
  normalized: { title: "Platform Engineer", company: "Local Co", location: "Remote",
    remote: true, salary: null, requirements: ["Python"], source_url: null },
};

beforeEach(() => {
  vi.mocked(listJobStaging).mockReset().mockResolvedValue([staged]);
  vi.mocked(importManualJob).mockReset().mockResolvedValue([staged]);
  vi.mocked(admitStagedJob).mockReset().mockResolvedValue({});
});
afterEach(cleanup);

it("keeps imports staged until the user admits them", async () => {
  render(<JobRadarPanel />);
  expect(await screen.findByRole("heading", { name: "Platform Engineer" })).toBeTruthy();
  expect(screen.getByText("缺口：Rust")).toBeTruthy();
  fireEvent.change(screen.getByLabelText("来源"), { target: { value: "manual://two" } });
  fireEvent.change(screen.getByLabelText("职位原文"), { target: { value: "Backend Engineer\nPython" } });
  fireEvent.click(screen.getByRole("button", { name: "导入暂存区" }));
  await waitFor(() => expect(importManualJob).toHaveBeenCalledTimes(1));
  expect(admitStagedJob).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "纳入机会" }));
  await waitFor(() => expect(admitStagedJob).toHaveBeenCalledWith("staging_001"));
});
