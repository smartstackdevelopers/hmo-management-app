export function canReadAiFeatureFlags(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.feature_flags.read"));
}

export function canManageAiFeatureFlags(permissions: string[] | undefined): boolean {
  return Boolean(permissions?.includes("ai.feature_flags.manage"));
}

export function statusLabel(item: {
  enabled?: boolean;
  pilot_enabled?: boolean;
  pilot_eligible?: boolean;
  configured?: boolean;
}): string {
  if (!item.configured) return "Disabled (no configuration)";
  if (!item.enabled) return "Disabled";
  if (item.pilot_eligible && !item.pilot_enabled) return "Enabled — pilot off";
  if (item.pilot_eligible && item.pilot_enabled) return "Pilot enabled";
  return "Enabled";
}
