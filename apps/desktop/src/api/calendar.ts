import type { InterviewRead } from "./history";

const roundLabels: Record<InterviewRead["round"], string> = {
  screen: "初筛",
  technical: "技术",
  loop: "综合",
  offer_talk: "Offer 沟通",
};

function escapeText(value: string): string {
  return value.replaceAll("\\", "\\\\").replaceAll(";", "\\;").replaceAll(",", "\\,").replaceAll("\r\n", "\\n").replaceAll("\n", "\\n");
}

function formatUtc(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) throw new Error("面试时间无效，无法导出日历");
  return date.toISOString().replaceAll("-", "").replaceAll(":", "").replace(/\.\d{3}Z$/, "Z");
}

function eventForInterview(interview: InterviewRead): string {
  const start = formatUtc(interview.scheduled_at);
  const end = new Date(new Date(interview.scheduled_at).getTime() + 60 * 60 * 1000).toISOString().replaceAll("-", "").replaceAll(":", "").replace(/\.\d{3}Z$/, "Z");
  const status = interview.status === "cancelled" ? "\r\nSTATUS:CANCELLED" : "";
  return [
    "BEGIN:VEVENT",
    `UID:${escapeText(interview.entity_id)}@career-agent-harness`,
    `DTSTAMP:${formatUtc(interview.scheduled_at)}`,
    `DTSTART:${start}`,
    `DTEND:${end}`,
    `SUMMARY:${escapeText(`观复 · ${roundLabels[interview.round]}面试`)}`,
    `DESCRIPTION:${escapeText(`申请 ${interview.application_id} · 申请版本 ${interview.application_revision} · 面试版本 ${interview.revision}`)}`,
    `X-ACH-APPLICATION-ID:${escapeText(interview.application_id)}`,
    `X-ACH-INTERVIEW-ID:${escapeText(interview.entity_id)}`,
    status.slice(2),
    "END:VEVENT",
  ].filter(Boolean).join("\r\n");
}

export function buildInterviewCalendar(interviews: InterviewRead[], now = new Date()): string {
  const stamp = now.toISOString().replaceAll("-", "").replaceAll(":", "").replace(/\.\d{3}Z$/, "Z");
  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Agent Career Harness//Guanfu//CN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    `X-WR-CALNAME:${escapeText("观复求职面试")}`,
    `X-WR-TIMEZONE:Asia/Shanghai`,
    `X-ACH-EXPORT-DTSTAMP:${stamp}`,
    ...interviews.slice().sort((a, b) => a.scheduled_at.localeCompare(b.scheduled_at)).map(eventForInterview),
    "END:VCALENDAR",
    "",
  ].join("\r\n");
}

export function downloadInterviewCalendar(interviews: InterviewRead[]): void {
  if (interviews.length === 0) throw new Error("暂无面试记录可导出");
  const blob = new Blob([buildInterviewCalendar(interviews)], { type: "text/calendar;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "guanfu-interviews.ics";
  anchor.click();
  URL.revokeObjectURL(url);
}
