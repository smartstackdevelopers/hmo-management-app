import { expect, test } from "@playwright/test";
import {
  canReviewDocumentCheck,
  canRunDocumentCheck,
  checkLayoutClass,
  findingLabel,
  observationLabel,
  visibleFindings,
} from "../src/lib/documentCheckView";

test.describe("document check view helpers", () => {
  test("labels rule, extraction, and AI observations separately", () => {
    expect(findingLabel("rule")).toBe("Rule-based");
    expect(findingLabel("ocr")).toBe("OCR / extraction");
    expect(observationLabel("llm", true)).toContain("not a verified fact");
    expect(observationLabel("structured_heuristic", false)).toContain("not a model decision");
  });

  test("permissions hide run and review controls", () => {
    expect(canRunDocumentCheck(["ai.document_check.run"])).toBe(true);
    expect(canRunDocumentCheck(["documents.read.meta"])).toBe(false);
    expect(canReviewDocumentCheck(["ai.document_check.review"])).toBe(true);
    expect(canReviewDocumentCheck(["ai.document_check.run"])).toBe(false);
  });

  test("shows page references and responsive layout", () => {
    const rows = visibleFindings([
      { code: "partial_text", title: "Short extract", page_number: 2, source: "ocr" },
      { code: "", title: "" },
    ]);
    expect(rows).toHaveLength(1);
    expect(rows[0]?.page_number).toBe(2);
    expect(checkLayoutClass()).toContain("sm:px-5");
  });
});
