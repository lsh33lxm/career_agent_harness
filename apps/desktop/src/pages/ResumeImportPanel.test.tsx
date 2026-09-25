// @vitest-environment jsdom

import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ResumeImportPanel } from "./ResumeImportPanel";

const mocks = vi.hoisted(() => ({ importResumeFile: vi.fn(), saveResumeBase: vi.fn() }));
vi.mock("../api/resumeStudio", () => ({ importResumeFile: mocks.importResumeFile }));
vi.mock("../api/projectResume", () => ({ saveResumeBase: mocks.saveResumeBase }));

describe("ResumeImportPanel", () => {
  beforeEach(() => {
    mocks.importResumeFile.mockReset();
    mocks.saveResumeBase.mockReset();
  });

  it("previews a local file and only saves after explicit confirmation", async () => {
    mocks.importResumeFile.mockResolvedValue({ valid: true, data: { name: "Minnn", skills: ["Python"] }, warnings: [], errors: [] });
    mocks.saveResumeBase.mockResolvedValue({});
    const onSaved = vi.fn();
    render(<ResumeImportPanel onSaved={onSaved} />);
    fireEvent.change(screen.getByLabelText("导入候选人 ID"), { target: { value: "candidate_001" } });
    fireEvent.change(screen.getByLabelText("导入新简历 ID"), { target: { value: "resume_imported_001" } });
    const input = document.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(["# Minnn\n## Skills\nPython"], "resume.md", { type: "text/markdown" });
    fireEvent.change(input, { target: { files: [file] } });
    expect(mocks.saveResumeBase).not.toHaveBeenCalled();
    await screen.findByText("提取预览");
    fireEvent.click(screen.getByRole("button", { name: "确认导入基础简历" }));
    await waitFor(() => expect(mocks.saveResumeBase).toHaveBeenCalledWith(expect.objectContaining({ resume_id: "resume_imported_001", candidate_id: "candidate_001" }), expect.any(String)));
    expect(onSaved).toHaveBeenCalled();
  });
});
