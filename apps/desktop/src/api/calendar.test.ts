import { describe, expect, it } from "vitest";

import { buildInterviewCalendar } from "./calendar";
import type { InterviewRead } from "./history";

const interview: InterviewRead = {
  entity_id: "interview_1",
  revision: 3,
  application_id: "application_1",
  application_revision: 2,
  round: "technical",
  scheduled_at: "2026-10-02T09:00:00+08:00",
  status: "scheduled",
  evidence_refs: [],
};

describe("buildInterviewCalendar", () => {
  it("uses a stable UID and UTC timestamps", () => {
    const calendar = buildInterviewCalendar([interview], new Date("2026-09-24T00:00:00Z"));
    expect(calendar).toContain("UID:interview_1@career-agent-harness");
    expect(calendar).toContain("DTSTART:20261002T010000Z");
    expect(calendar).toContain("DTEND:20261002T020000Z");
    expect(calendar).toContain("SUMMARY:观复 · 技术面试");
    expect(calendar).toContain("X-ACH-APPLICATION-ID:application_1");
  });

  it("marks cancelled interviews without changing their stable identity", () => {
    const calendar = buildInterviewCalendar([{ ...interview, status: "cancelled" }]);
    expect(calendar).toContain("UID:interview_1@career-agent-harness");
    expect(calendar).toContain("STATUS:CANCELLED");
  });

  it("sorts events by scheduled time", () => {
    const later = { ...interview, entity_id: "interview_2", scheduled_at: "2026-10-03T09:00:00+08:00" };
    const calendar = buildInterviewCalendar([later, interview]);
    expect(calendar.indexOf("UID:interview_1@career-agent-harness")).toBeLessThan(calendar.indexOf("UID:interview_2@career-agent-harness"));
  });
});
