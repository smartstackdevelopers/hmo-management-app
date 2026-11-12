export const OCCUPANCY_PHASE6_NOTICE =
  'Phase 6 site surveys only on this view. Live estimated people counts require occupancy.read and a completed privacy approval gate — tenants never see live occupancy.';

export const LIVE_OCCUPANCY_PRIVACY_NOTICE =
  'Estimated people counts only. No facial recognition or identity tracking. Offline rooms do not show as zero occupants. Live cameras stay off until organisational privacy approvals are complete.';

export interface OccupancySurveySummary {
  id: string;
  property_id: string;
  status: string;
  survey_date: string | null;
  feasibility_status: string | null;
  feasibility_summary: string | null;
}

function asText(value: unknown): string | null {
  if (typeof value !== 'string') return null;
  const trimmed = value.trim();
  return trimmed || null;
}

/** Copies survey summary fields only. Count-like fields from a payload are dropped. */
export function surveySummariesFromResponse(data: unknown): OccupancySurveySummary[] {
  const items = data && typeof data === 'object' && Array.isArray((data as { items?: unknown }).items)
    ? (data as { items: unknown[] }).items
    : [];
  return items.flatMap((item) => {
    if (!item || typeof item !== 'object') return [];
    const record = item as Record<string, unknown>;
    const id = asText(record.id);
    const propertyId = asText(record.property_id);
    const status = asText(record.status);
    if (!id || !propertyId || !status) return [];
    const summary: OccupancySurveySummary = {
      id,
      property_id: propertyId,
      status,
      survey_date: asText(record.survey_date),
      feasibility_status: asText(record.feasibility_status),
      feasibility_summary: asText(record.feasibility_summary),
    };
    return [summary];
  });
}
