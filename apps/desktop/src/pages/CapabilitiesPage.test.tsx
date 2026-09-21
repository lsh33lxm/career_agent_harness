// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";

import { listCapabilityInbox, reviewCapabilityCandidate } from "../api/capabilityInbox";
import {
  getCapabilities,
  listCapabilityIdentities,
  type CapabilityProjection,
  type CapabilityWorkspace,
} from "../api/capabilities";
import { CapabilitiesPage } from "./CapabilitiesPage";
import { CapabilityInboxPage } from "./CapabilityInboxPage";

vi.mock("../api/capabilities", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/capabilities")>();
  return { ...original, getCapabilities: vi.fn(), listCapabilityIdentities: vi.fn() };
});
vi.mock("../api/capabilityInbox", () => ({ listCapabilityInbox: vi.fn(), reviewCapabilityCandidate: vi.fn() }));

function projection(capabilityId: string, populated = false): CapabilityProjection {
  return {
    capability_id: capabilityId,
    personal_state: populated ? {
      personal_state_id: "state_001", candidate_id: "candidate_001", capability_id: capabilityId,
      understand: true, explain: true, apply: true, evidence: true, interview_ready: false,
      revision: 2, display_status: "verified", updated_at: "2026-09-20T08:00:00Z",
    } : null,
    evidence_bindings: [],
    target_market_bindings: populated ? [{ binding_id: "target_1", market_scope: "target", source_evidence_refs: [], opportunity_id: "opportunity_1", job_requirement_id: null }] : [],
    broad_market_bindings: populated ? [{ binding_id: "broad_1", market_scope: "broad", source_evidence_refs: [], opportunity_id: null, job_requirement_id: null }] : [],
    investment_state: populated ? { investment_state_id: "investment_1", recommendation: "high", score: 0.86, reasons: ["目标市场需求较强。"], rule_version: "v1", calculated_at: "2026-09-20T08:00:00Z" } : null,
  };
}

function workspace(populated = true): CapabilityWorkspace {
  return {
    candidate_id: "candidate_001",
    graph_version: { graph_version_id: "graph_001", version_label: "1.0", parent_graph_version_id: null, change_note: "初始图谱", released_at: "2026-09-20T08:00:00Z", released_by: "user", released_by_kind: "user" },
    nodes: [
      { capability_id: "capability_alpha", canonical_name: "能力甲", description: "第一项", layer: "common_core", lifecycle_status: "active", graph_version_id: "graph_001" },
      { capability_id: "capability_beta", canonical_name: "能力乙", description: "第二项", layer: "track", lifecycle_status: "active", graph_version_id: "graph_001" },
    ],
    relations: [{ relation_id: "relation_1", source_capability_id: "capability_alpha", target_capability_id: "capability_beta", relation_type: "prerequisite", graph_version_id: "graph_001" }],
    projections: [projection("capability_alpha", populated), projection("capability_beta")],
    input_revisions: [{ kind: "graph_version", entity_id: "graph_001", revision: null }],
    workspace_version: "capability-workspace-v1",
  };
}

beforeEach(() => {
  vi.mocked(getCapabilities).mockReset();
  vi.mocked(listCapabilityIdentities).mockReset().mockResolvedValue(["candidate_001"]);
});
afterEach(cleanup);

describe("CapabilitiesPage", () => {
  it("自动选择已有个人档案并加载能力地图", async () => {
    vi.mocked(getCapabilities).mockResolvedValue(workspace());
    render(<MemoryRouter><CapabilitiesPage /></MemoryRouter>);

    expect(await screen.findByText("官方节点")).toBeTruthy();
    expect(getCapabilities).toHaveBeenCalledWith("candidate_001", undefined, expect.any(AbortSignal));
    expect(screen.queryByText(/候选人 ID|图谱版本 ID/)).toBeNull();
    expect((screen.getByLabelText("选择个人能力档案") as HTMLSelectElement).value).toBe("candidate_001");
  });

  it("保持官方图谱、个人覆盖、市场信号和投资提案的边界", async () => {
    vi.mocked(getCapabilities).mockResolvedValue(workspace());
    render(<MemoryRouter><CapabilitiesPage /></MemoryRouter>);
    await screen.findByRole("button", { name: /能力甲/ });

    expect(screen.getByRole("heading", { name: "个人状态" })).toBeTruthy();
    expect(screen.getByText("目标市场绑定")).toBeTruthy();
    expect(screen.getByText("广泛市场绑定")).toBeTruthy();
    expect(screen.getByText("建议 高")).toBeTruthy();
    expect(screen.getByText("这是提案，不是用户优先级。")).toBeTruthy();
  });

  it("无个人档案时给出可执行中文引导", async () => {
    vi.mocked(listCapabilityIdentities).mockResolvedValue([]);
    render(<MemoryRouter><CapabilitiesPage /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "还没有个人能力档案" })).toBeTruthy();
    expect(getCapabilities).not.toHaveBeenCalled();
  });

  it("读取失败时可重试同一档案", async () => {
    vi.mocked(getCapabilities).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(workspace());
    render(<MemoryRouter><CapabilitiesPage /></MemoryRouter>);
    const alert = await screen.findByRole("alert");
    fireEvent.click(within(alert).getByRole("button", { name: "重试" }));
    expect(await screen.findByText("官方节点")).toBeTruthy();
    expect(getCapabilities).toHaveBeenCalledTimes(2);
  });
});

it("能力候选审核后返回原精确查询上下文", async () => {
  vi.mocked(getCapabilities).mockResolvedValue(workspace());
  const candidate = { candidate_node_id: "candidate_node_001", proposed_canonical_name: "候选能力", proposed_description: "待审核", proposed_layer: "track", source_evidence_refs: ["evidence_001"], discovered_by: "agent:scout", status: "pending" as const, reviewed_by: null, reviewed_by_kind: null, review_reason: null, merge_target_capability_id: null };
  vi.mocked(listCapabilityInbox).mockResolvedValue([{ candidate, revision: 1 }]);
  vi.mocked(reviewCapabilityCandidate).mockResolvedValue({ candidate: { ...candidate, status: "ignored" }, commit: { entity_id: candidate.candidate_node_id, revision: 2, revision_id: "revision_2", event_id: "event_2" }, capability_id: null, graph_version: null });

  render(<MemoryRouter initialEntries={[{ pathname: "/capabilities", state: { capabilityQuery: { candidateId: "candidate_001", graphVersionId: "graph_001" } } }]}><Routes><Route path="/capabilities" element={<CapabilitiesPage />} /><Route path="/capabilities/inbox" element={<CapabilityInboxPage />} /></Routes></MemoryRouter>);
  await screen.findByText("官方节点");
  fireEvent.click(screen.getByRole("link", { name: "审核能力候选" }));
  await screen.findByText("候选能力");
  fireEvent.change(screen.getByLabelText("审核决定"), { target: { value: "reject" } });
  fireEvent.change(screen.getByLabelText("审核理由"), { target: { value: "证据不足" } });
  fireEvent.click(screen.getByRole("button", { name: "确认审核" }));
  await screen.findByText("审核已成功");
  fireEvent.click(screen.getByRole("link", { name: "返回能力地图" }));
  await screen.findByText("官方节点");
  expect(vi.mocked(getCapabilities).mock.calls.at(-1)).toEqual(["candidate_001", "graph_001", expect.any(AbortSignal)]);
});
