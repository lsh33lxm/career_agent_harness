// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { admitStagedJob } from "../api/jobRadar";
import {
  getLegacyImportStatus,
  getLegacyJob,
  listLegacyJobs,
  runLegacyImport,
  type LegacyImportReport,
  type LegacyJobSummary,
} from "../api/legacy";
import { JobRadarPanel } from "./JobRadarPanel";

vi.mock("../api/jobRadar", () => ({ admitStagedJob: vi.fn() }));
vi.mock("../api/legacy", () => ({
  getLegacyImportStatus: vi.fn(),
  getLegacyJob: vi.fn(),
  listLegacyJobs: vi.fn(),
  runLegacyImport: vi.fn(),
}));

const job: LegacyJobSummary = {
  staging_id: "staging_001",
  title: "Agent Harness 工程师",
  company: "观复科技",
  location: '["北京", "远程"]',
  salary: "30-45K",
  source_url: "https://example.com/jobs/1",
  status: "staged",
  duplicate_of: null,
  suggested_score: 0.86,
  review_status: "historical_unconfirmed",
  source_path: "data/统一数据/岗位与JD数据.csv",
  source_class: "job",
  source_sha256: "a".repeat(64),
  row_number: 161,
  imported_at: "2026-09-21T10:00:00Z",
  tags: ['["Python", "React"]'],
};

const report: LegacyImportReport = {
  batch_id: "batch_001",
  source_root: "D:/legacy",
  source_signature_before: "before",
  source_signature_after: "before",
  status: "completed",
  started_at: "2026-09-21T10:00:00Z",
  finished_at: "2026-09-21T10:01:00Z",
  files: [],
  totals: { read_count: 7575, new_count: 1028, duplicate_count: 684, failed_count: 0 },
  importer_version: "1.0",
};

beforeEach(() => {
  vi.mocked(getLegacyImportStatus).mockReset().mockResolvedValue({
    configured_source_root: "D:/legacy",
    source_accessible: true,
    latest_report: report,
  });
  vi.mocked(listLegacyJobs).mockReset().mockResolvedValue([job]);
  vi.mocked(getLegacyJob).mockReset().mockResolvedValue({
    job,
    jd_text: "负责 <b>Agent Harness</b> 平台开发",
    raw_record: {},
    transform: {},
    batch_id: "batch_001",
    related_interviews: [{ title: "技术一面", interview_date: "2026-09-18" }],
  });
  vi.mocked(runLegacyImport).mockReset().mockResolvedValue(report);
  vi.mocked(admitStagedJob).mockReset().mockResolvedValue({});
});

afterEach(cleanup);

describe("JobRadarPanel", () => {
  it("默认展示真实岗位并可搜索和查看来源溯源", async () => {
    render(<JobRadarPanel />);
    expect(await screen.findByRole("heading", { name: "Agent Harness 工程师" })).toBeTruthy();
    expect(screen.getByText("北京、远程 · 30-45K")).toBeTruthy();
    expect(screen.getByText("Python")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("搜索岗位、公司或技能"), {
      target: { value: "Python" },
    });
    fireEvent.click(screen.getByRole("button", { name: "搜索" }));
    await waitFor(() => expect(listLegacyJobs).toHaveBeenLastCalledWith(
      expect.objectContaining({ query: "Python", limit: 100 }),
    ));

    fireEvent.click(screen.getAllByRole("button", { name: "查看详情" })[0]);
    expect(await screen.findByText("data/统一数据/岗位与JD数据.csv")).toBeTruthy();
    expect(screen.getByText("161")).toBeTruthy();
    expect(screen.getByText("技术一面 · 2026-09-18")).toBeTruthy();
    expect(screen.getByText(/负责 Agent Harness 平台开发/)).toBeTruthy();
  });

  it("由用户触发可审计导入并明确加入求职流程", async () => {
    render(<JobRadarPanel />);
    await screen.findByRole("heading", { name: "Agent Harness 工程师" });
    fireEvent.click(screen.getByRole("button", { name: "重新核验导入" }));
    await waitFor(() => expect(runLegacyImport).toHaveBeenCalledWith("D:/legacy"));
    fireEvent.click(screen.getByRole("button", { name: "加入求职流程" }));
    await waitFor(() => expect(admitStagedJob).toHaveBeenCalledWith("staging_001"));
  });
});
