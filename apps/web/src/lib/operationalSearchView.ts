export const OPERATIONAL_SEARCH_NOTICE =
  "Natural-language search returns authorised operational records only. It does not change records and does not run database commands from the question.";

export function canRunOperationalSearch(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("operational_search.run"));
}

export function outcomeLabel(outcome: string): string {
  switch (outcome) {
    case "results":
      return "Results";
    case "clarification":
      return "Clarification needed";
    case "unsupported":
      return "Search not supported";
    default:
      return outcome;
  }
}
