export const OCCUPANCY_PHASE6_NOTICE =
  'Live camera counts are not available in this app. They are planned for Phase 6. This screen lists occupancy site surveys only and does not show a people count.';

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
