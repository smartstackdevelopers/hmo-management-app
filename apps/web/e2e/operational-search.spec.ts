import { expect, test } from "@playwright/test";
import { OPERATIONAL_SEARCH_NOTICE, canRunOperationalSearch, outcomeLabel } from "../src/lib/operationalSearchView";

test.describe("operational search helpers", () => {
  test("labels outcomes and requires permission", () => {
    expect(OPERATIONAL_SEARCH_NOTICE).toContain("does not run database commands");
    expect(outcomeLabel("clarification")).toBe("Clarification needed");
    expect(outcomeLabel("unsupported")).toBe("Search not supported");
    expect(canRunOperationalSearch([])).toBe(false);
    expect(canRunOperationalSearch(["operational_search.run"])).toBe(true);
  });
});
