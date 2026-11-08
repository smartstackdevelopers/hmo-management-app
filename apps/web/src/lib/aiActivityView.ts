export const CONFIDENCE_UNAVAILABLE = "Confidence unavailable";

export const FEEDBACK_CATEGORIES = [
  { value: "incorrect_information", label: "Incorrect information" },
  { value: "incomplete_answer", label: "Incomplete answer" },
  { value: "misleading_answer", label: "Misleading answer" },
  { value: "unsupported_claim", label: "Unsupported claim" },
  { value: "missing_source", label: "Missing source" },
  { value: "outdated_information", label: "Outdated information" },
  { value: "other", label: "Other" },
] as const;

export function canReadAiActivity(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.activity.read"));
}

export function canSubmitAiFeedback(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.activity.feedback.submit"));
}

export function canReviewAiFeedback(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.activity.feedback.review"));
}

export function formatConfidence(confidence: {
  kind?: string;
  label?: string;
  calibrated?: boolean;
  percentage?: number | null;
} | null | undefined): string {
  if (!confidence) return CONFIDENCE_UNAVAILABLE;
  if (confidence.percentage != null) {
    // Never display fabricated percentages from the client either.
    return confidence.label || CONFIDENCE_UNAVAILABLE;
  }
  if (confidence.kind === "unavailable" || !confidence.kind) {
    return CONFIDENCE_UNAVAILABLE;
  }
  return confidence.label || CONFIDENCE_UNAVAILABLE;
}
