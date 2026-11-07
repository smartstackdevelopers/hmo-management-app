export type FindingView = {
  id?: string;
  code?: string;
  source?: string;
  outcome?: string;
  title?: string;
  detail?: string;
  page_number?: number | null;
  review_status?: string;
  origin?: string;
};

export function findingLabel(source: string | undefined): string {
  if (source === "rule") return "Rule-based";
  if (source === "ocr") return "OCR / extraction";
  if (source === "ai") return "AI-generated";
  return "Recorded check";
}

export function observationLabel(origin: string | undefined, aiGenerated: boolean): string {
  if (aiGenerated || origin === "llm") return "AI-generated observation — not a verified fact";
  return "Explanation of recorded checks — not a model decision";
}

export function canRunDocumentCheck(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.document_check.run"));
}

export function canReviewDocumentCheck(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.document_check.review"));
}

export function checkLayoutClass(): string {
  return "space-y-4 rounded-lg border border-slate-200 bg-white p-4 px-4 sm:px-5";
}

export function visibleFindings(findings: FindingView[]): FindingView[] {
  return findings.filter((item) => item.title || item.code);
}
