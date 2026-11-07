export const DUPLICATE_DETECTION_NOTICE =
  "Potential Duplicates — Human Review Required. Similarity indicates matching strength only and does not prove identity. This feature never deletes or merges records automatically.";

export function canRunDuplicateDetection(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("duplicate_detection.run"));
}

export function canReadDuplicateDetection(permissions: string[] | undefined): boolean {
  return Boolean(
    permissions?.includes("duplicate_detection.read") ||
      permissions?.includes("duplicate_detection.run") ||
      permissions?.includes("duplicate_detection.review"),
  );
}

export function canReviewDuplicateFindings(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("duplicate_detection.review"));
}

export function matchStrengthLabel(strength: string): string {
  switch (strength) {
    case "exact":
      return "Exact field match";
    case "strong":
      return "Strong match signals";
    case "possible":
      return "Possible match — review carefully";
    default:
      return strength;
  }
}

export function reviewStatusLabel(status: string): string {
  switch (status) {
    case "pending":
      return "Pending human review";
    case "confirmed_duplicate":
      return "Confirmed duplicate (records unchanged)";
    case "not_duplicate":
      return "Marked not a duplicate";
    case "deferred":
      return "Deferred";
    default:
      return status;
  }
}

export function analysisLayoutClass(): string {
  return "space-y-4 rounded-lg border border-amber-200 bg-amber-50/40 p-4";
}
