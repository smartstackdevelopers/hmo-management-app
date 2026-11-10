const UUID = /[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}/i;

const ROUTES: Record<string, (id: string) => string> = {
  incident: (id) => `/(app)/staff/incident/${id}`,
  maintenance_request: (id) => `/(app)/staff/work-order/${id}`,
  work_order: (id) => `/(app)/staff/work-order/${id}`,
  tenant_visit: (id) => `/(app)/staff/visits?visitId=${id}`,
  visit: (id) => `/(app)/staff/visits?visitId=${id}`,
  operational_task: (id) => `/(app)/staff/tasks?taskId=${id}`,
  task: (id) => `/(app)/staff/tasks?taskId=${id}`,
  tenant: (id) => `/(app)/staff/case/${id}`,
  daily_log: () => '/(app)/(tabs)/notes',
  occupancy_site_survey: () => '/(app)/staff/occupancy',
};

export interface StaffAlertLinkInput {
  related_resource_type?: string | null;
  related_resource_id?: string | null;
  subject?: string | null;
  body?: string | null;
}

/** Opens a staff record only when the message names a known resource. */
export function staffAlertHref(input: StaffAlertLinkInput): string | null {
  const typed = input.related_resource_type?.trim().toLowerCase();
  const id = input.related_resource_id?.trim();
  if (typed && ROUTES[typed]) {
    if (typed === 'daily_log' || typed === 'occupancy_site_survey') return ROUTES[typed](id || '');
    if (id && UUID.test(id)) return ROUTES[typed](id);
  }
  const text = `${input.subject ?? ''}\n${input.body ?? ''}`;
  const explicit = text.match(/hmore:\/\/([a-z_]+)\/([0-9a-f-]{36})/i);
  if (!explicit) return null;
  const kind = explicit[1].toLowerCase();
  if (!ROUTES[kind] || !UUID.test(explicit[2])) return null;
  return ROUTES[kind](explicit[2]);
}
