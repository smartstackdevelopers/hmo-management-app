import { expect, test } from "@playwright/test";
import { isComplaintOverdue, priorityBadgeClass } from "../src/lib/complaintsApi";

test.describe("complaints helpers (unit via Playwright runner)", () => {
  test("priority badge classes highlight urgent", () => {
    expect(priorityBadgeClass("urgent")).toContain("red");
    expect(priorityBadgeClass("normal")).toContain("sky");
  });

  test("overdue helper uses backend flag", () => {
    expect(isComplaintOverdue({ is_overdue: true })).toBe(true);
    expect(isComplaintOverdue({ is_overdue: false })).toBe(false);
  });
});
