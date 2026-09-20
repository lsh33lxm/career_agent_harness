// @vitest-environment jsdom
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  getCapabilities,
  type CapabilityProjection,
  type CapabilityWorkspace,
} from "../api/capabilities";
import { CapabilitiesPage } from "./CapabilitiesPage";

vi.mock("../api/capabilities", async (importOriginal) => {
  const original = await importOriginal<typeof import("../api/capabilities")>();
  return { ...original, getCapabilities: vi.fn() };
});

function projection(capabilityId: string, populated = false): CapabilityProjection {
  return {
    capability_id: capabilityId,
    personal_state: populated ? {
      personal_state_id: "state_001",
      candidate_id: "candidate_001",
      capability_id: capabilityId,
      understand: true,
      explain: true,
      apply: true,
      evidence: true,
      interview_ready: false,
      revision: 2,
      display_status: "verified",
      updated_at: "2026-09-20T08:00:00Z",
    } : null,
    evidence_bindings: populated ? [{
      binding_id: "evidence_binding_001",
      evidence_ref_id: "evidence_ref_001",
      project_evidence_id: null,
      project_evidence_revision: null,
      authority: "document_supported",
      scopes: ["explain"],
    }] : [],
    target_market_bindings: populated ? [{
      binding_id: "target_binding_001",
      market_scope: "target",
      source_evidence_refs: ["target_source"],
      opportunity_id: "opportunity_001",
      job_requirement_id: null,
    }] : [],
    broad_market_bindings: populated ? [{
      binding_id: "broad_binding_001",
      market_scope: "broad",
      source_evidence_refs: ["broad_source"],
      opportunity_id: null,
      job_requirement_id: null,
    }] : [],
    investment_state: populated ? {
      investment_state_id: "investment_001",
      recommendation: "high",
      score: 0.86,
      reasons: ["目标市场需求较强。"],
      rule_version: "capability-investment-v1",
      calculated_at: "2026-09-20T08:00:00Z",
    } : null,
  };
}

function workspace(populated = true): CapabilityWorkspace {
  return {
    candidate_id: "candidate_001",
    graph_version: {
      graph_version_id: "graph_001",
      version_label: "1.0",
      parent_graph_version_id: null,
      change_note: "Initial graph.",
      released_at: "2026-09-20T08:00:00Z",
      released_by: "user",
      released_by_kind: "user",
    },
    nodes: [
      {
        capability_id: "capability_alpha",
        canonical_name: "Alpha",
        description: "First in Core order.",
        layer: "common_core",
        lifecycle_status: "active",
        graph_version_id: "graph_001",
      },
      {
        capability_id: "capability_beta",
        canonical_name: "Beta",
        description: "Second in Core order.",
        layer: "track",
        lifecycle_status: "active",
        graph_version_id: "graph_001",
      },
    ],
    relations: [{
      relation_id: "relation_001",
      source_capability_id: "capability_alpha",
      target_capability_id: "capability_beta",
      relation_type: "prerequisite",
      graph_version_id: "graph_001",
    }],
    projections: [projection("capability_alpha", populated), projection("capability_beta")],
    input_revisions: [{ kind: "graph_version", entity_id: "graph_001", revision: null }],
    workspace_version: "capability-workspace-v1",
  };
}

function submitCandidate(candidateId = "candidate_001", graphVersionId = "") {
  fireEvent.change(screen.getByLabelText("候选人 ID"), { target: { value: candidateId } });
  if (graphVersionId) {
    fireEvent.change(screen.getByLabelText(/图谱版本 ID/), {
      target: { value: graphVersionId },
    });
  }
  fireEvent.click(screen.getByRole("button", { name: "加载能力地图" }));
}

beforeEach(() => {
  vi.mocked(getCapabilities).mockReset();
});

afterEach(cleanup);

describe("CapabilitiesPage", () => {
  it("requires explicit identity and passes optional exact graph selection", async () => {
    vi.mocked(getCapabilities).mockResolvedValue(workspace());
    render(<CapabilitiesPage />);

    expect(screen.getByText("请选择候选人")).toBeTruthy();
    expect(getCapabilities).not.toHaveBeenCalled();
    submitCandidate("candidate_001", "graph_001");

    expect(await screen.findByText("官方节点")).toBeTruthy();
    expect(getCapabilities).toHaveBeenCalledWith(
      "candidate_001",
      "graph_001",
      expect.any(AbortSignal),
    );
  });

  it("renders nodes in exact Core order and keeps target, broad and proposal labels separate", async () => {
    vi.mocked(getCapabilities).mockResolvedValue(workspace());
    render(<CapabilitiesPage />);
    submitCandidate();

    await screen.findByRole("button", { name: /Alpha/ });
    const nodeButtons = Array.from(
      document.querySelectorAll<HTMLButtonElement>(".capability-node-list button"),
    );
    expect(nodeButtons.map((button) => button.textContent)).toEqual([
      expect.stringContaining("Alpha"),
      expect.stringContaining("Beta"),
    ]);
    expect(screen.getByRole("heading", { name: "个人状态" })).toBeTruthy();
    expect(screen.getByText("目标市场绑定")).toBeTruthy();
    expect(screen.getByText("广泛市场绑定")).toBeTruthy();
    expect(screen.getByText("capability_alpha → capability_beta")).toBeTruthy();
    expect(screen.getByText("建议 高")).toBeTruthy();
    expect(screen.getByText("这是提案，不是用户优先级。")).toBeTruthy();
  });

  it("renders graph-without-overlay and remains inspectable at a 320px viewport", async () => {
    Object.defineProperty(window, "innerWidth", { configurable: true, value: 320 });
    vi.mocked(getCapabilities).mockResolvedValue(workspace(false));
    render(<CapabilitiesPage />);
    submitCandidate();

    const alpha = await screen.findByRole("button", { name: /Alpha/ });
    expect(alpha.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByText("该候选人暂无个人覆盖层。")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Beta/ }));
    expect(screen.getByRole("heading", { name: "Beta" })).toBeTruthy();
    expect(document.querySelector(".capability-workspace-layout")).toBeTruthy();
  });

  it("renders empty graph and retries API errors", async () => {
    const empty: CapabilityWorkspace = {
      candidate_id: "candidate_001",
      graph_version: null,
      nodes: [],
      relations: [],
      projections: [],
      input_revisions: [],
      workspace_version: "capability-workspace-v1",
    };
    vi.mocked(getCapabilities)
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(empty);
    render(<CapabilitiesPage />);
    submitCandidate();

    const alert = await screen.findByRole("alert");
    expect(within(alert).getByText("能力地图不可用")).toBeTruthy();
    fireEvent.click(within(alert).getByRole("button", { name: "重试" }));
    expect(await screen.findByText("暂无官方能力图谱")).toBeTruthy();
    expect(getCapabilities).toHaveBeenCalledTimes(2);
  });
});
