import { expect, test } from "@playwright/test";
import {
  canManageAiFeatureFlags,
  canReadAiFeatureFlags,
  statusLabel,
} from "../src/lib/aiFeatureFlagsView";

test.describe("AI feature flags helpers", () => {
  test("permissions and status labels", () => {
    expect(canReadAiFeatureFlags([])).toBe(false);
    expect(canReadAiFeatureFlags(["ai.feature_flags.read"])).toBe(true);
    expect(canManageAiFeatureFlags(["ai.feature_flags.read"])).toBe(false);
    expect(canManageAiFeatureFlags(["ai.feature_flags.manage"])).toBe(true);
    expect(statusLabel({ configured: false })).toContain("no configuration");
    expect(statusLabel({ configured: true, enabled: false })).toBe("Disabled");
    expect(
      statusLabel({ configured: true, enabled: true, pilot_eligible: true, pilot_enabled: true }),
    ).toBe("Pilot enabled");
  });
});
