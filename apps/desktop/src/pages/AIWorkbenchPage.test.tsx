// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AIWorkbenchPage } from "./AIWorkbenchPage";

const mocks = vi.hoisted(() => ({
  listOpportunities: vi.fn(), listResumeBases: vi.fn(), listApplications: vi.fn(),
  listMemories: vi.fn(), createCommunicationDraft: vi.fn(),
}));

vi.mock("../api/client", () => ({ listOpportunities: mocks.listOpportunities }));
vi.mock("../api/projectResume", () => ({ listResumeBases: mocks.listResumeBases }));
vi.mock("../api/history", () => ({ listApplications: mocks.listApplications }));
vi.mock("../api/memory", () => ({ listMemories: mocks.listMemories }));
vi.mock("../api/communications", () => ({ createCommunicationDraft: mocks.createCommunicationDraft }));

describe("AIWorkbenchPage", () => {
  beforeEach(() => {
    mocks.listOpportunities.mockResolvedValue([{ opportunity: { entity_id: "opp_1", revision: 1, state: "preparing" } }]);
    mocks.listResumeBases.mockResolvedValue([{ resume_id: "resume_1", revision: 2 }]);
    mocks.listApplications.mockResolvedValue([{ entity_id: "app_1", state: "preparing" }]);
    mocks.listMemories.mockResolvedValue([]);
    mocks.createCommunicationDraft.mockResolvedValue({ draft_id: "draft_1" });
  });

  it("binds stable IDs and saves generated output as a pending draft", async () => {
    render(<MemoryRouter><AIWorkbenchPage /></MemoryRouter>);
    await screen.findByText(/岗位 opp_1/);
    fireEvent.change(screen.getByLabelText("你的问题"), { target: { value: "补证据" } });
    fireEvent.click(screen.getByRole("button", { name: "生成建议" }));
    fireEvent.click(await screen.findByRole("button", { name: "保存到待确认草稿" }));
    await waitFor(() => expect(mocks.createCommunicationDraft).toHaveBeenCalledWith(expect.objectContaining({
      opportunity_id: "opp_1",
      provenance: expect.objectContaining({ resume_id: "resume_1", application_id: "app_1" }),
    })));
  });
});
