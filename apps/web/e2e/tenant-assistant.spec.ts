import { expect, test } from "@playwright/test";
import { ASSISTANT_NOTICE, canAskTenantAssistant, sourceLabel } from "../src/lib/tenantAssistantView";

test.describe("tenant assistant helpers", () => {
  test("shows information-only notice and source labels", () => {
    expect(ASSISTANT_NOTICE).toContain("does not make official operational decisions");
    expect(sourceLabel("communication_announcement")).toBe("Approved announcement");
  });

  test("only tenants with ask permission can use the assistant", () => {
    expect(canAskTenantAssistant(["ai.tenant_assistant.ask"], "tenant")).toBe(true);
    expect(canAskTenantAssistant(["ai.tenant_assistant.ask"], "organisation_admin")).toBe(false);
    expect(canAskTenantAssistant([], "tenant")).toBe(false);
  });
});
