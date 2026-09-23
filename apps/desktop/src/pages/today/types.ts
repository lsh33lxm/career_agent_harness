export type PriorityLevel = "low" | "medium" | "high" | "urgent";

export interface TodayViewModel {
  dateLabel: string;
  focus: { title: string; description: string; actionLabel: string; evidenceLabel: string };
  opportunities: Array<{
    id: string; company: string; role: string; location: string; source: string;
    matchPercent: number; suggestedPriority: PriorityLevel; userPriority: PriorityLevel; reason: string;
  }>;
  confirmations: Array<{
    id: string; title: string; subtitle: string; source: string; date: string;
    description: string; actionLabel: string;
  }>;
  weeklySteps: Array<{ label: string; date: string; state: "done" | "current" | "upcoming" }>;
  completedSteps: number;
}
