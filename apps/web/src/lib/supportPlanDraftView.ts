export type DraftGoal = {
  title?: string;
  description?: string;
  actions?: string[];
  milestones?: Array<{ title?: string; description?: string }>;
  source_refs?: Array<{ type?: string; id?: string }>;
};

export type DraftContent = {
  situation?: string;
  recorded_needs?: string[];
  recorded_goals?: string[];
  suggested_goals?: DraftGoal[];
  gaps?: string[];
  responsibility_note?: string;
};

export function canRunSupportPlanDraft(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.support_plan_draft.run"));
}

export function canReviewSupportPlanDraft(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.support_plan_draft.review"));
}

export function canApplySupportPlanDraft(permissions: string[] | undefined, status: string | undefined): boolean {
  return Boolean(permissions?.includes("support_plans.manage") && status === "approved");
}

export function draftLayoutClass(): string {
  return "space-y-4 rounded-lg border border-amber-200 bg-amber-50 p-4 sm:px-5";
}

export function originLabel(origin: string | undefined): string {
  if (origin === "human_edited") return "Human-edited draft — not an approved support plan";
  return "AI-generated draft — not an approved support plan";
}

export function visibleGaps(gaps: string[] | undefined): string[] {
  return (gaps ?? []).filter((item) => item.trim().length > 0);
}
