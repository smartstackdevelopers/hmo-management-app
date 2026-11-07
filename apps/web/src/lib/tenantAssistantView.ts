export const ASSISTANT_NOTICE =
  "Information only — the Tenant Assistant answers from approved organisation content and does not make official operational decisions.";

export function canAskTenantAssistant(permissions: string[] | undefined, role?: string | null): boolean {
  return role === "tenant" && Boolean(permissions?.includes("ai.tenant_assistant.ask"));
}

export function sourceLabel(sourceType: string): string {
  if (sourceType === "communication_announcement") return "Approved announcement";
  if (sourceType === "maintenance_emergency_content") return "Approved emergency guidance";
  return sourceType;
}
