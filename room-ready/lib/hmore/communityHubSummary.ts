/**
 * Pure formatters for the F5.6 Community hub.
 * Never invent counts — return null/empty when API data is missing.
 */

export function communityDirectorySummary(input: {
  total?: number | null;
  error?: boolean;
}): string | null {
  if (input.error) return null;
  if (typeof input.total !== 'number') return null;
  if (input.total <= 0) return 'No published local services yet.';
  return `${input.total} published local service${input.total === 1 ? '' : 's'}.`;
}

export function employmentApplicationsSummary(input: {
  total?: number | null;
  preparing?: number | null;
  interviews?: number | null;
  error?: boolean;
}): string | null {
  if (input.error) return null;
  const total = typeof input.total === 'number' ? input.total : null;
  if (total == null) return null;
  if (total <= 0) return 'No job applications recorded yet.';
  const interviews = typeof input.interviews === 'number' ? input.interviews : 0;
  const preparing = typeof input.preparing === 'number' ? input.preparing : 0;
  return `${total} application${total === 1 ? '' : 's'} · ${preparing} preparing · ${interviews} interview${interviews === 1 ? '' : 's'}.`;
}

export function savedJobsSummary(input: { total?: number | null; error?: boolean }): string | null {
  if (input.error) return null;
  if (typeof input.total !== 'number') return null;
  if (input.total <= 0) return 'No saved jobs yet.';
  return `${input.total} saved job${input.total === 1 ? '' : 's'}.`;
}

export function trainingSummary(input: { total?: number | null; error?: boolean }): string | null {
  if (input.error) return null;
  if (typeof input.total !== 'number') return null;
  if (input.total <= 0) return 'No training recommendations yet.';
  return `${input.total} training suggestion${input.total === 1 ? '' : 's'}.`;
}

/** Tenant-private wellbeing status only — never for staff or shared dashboards. */
export function wellbeingPrivateSummary(input: {
  todayCheckin?: boolean | null;
  latestMood?: string | null;
  completed?: number | null;
  planned?: number | null;
  error?: boolean;
}): string | null {
  if (input.error) return null;
  if (input.todayCheckin == null && input.latestMood == null && input.planned == null) return null;
  const checkin = input.todayCheckin ? 'Check-in done today' : 'Check-in not done today';
  const mood = input.latestMood ? ` · Mood: ${String(input.latestMood).replace(/_/g, ' ')}` : '';
  const planned = typeof input.planned === 'number' ? input.planned : 0;
  const completed = typeof input.completed === 'number' ? input.completed : 0;
  const routines = planned > 0 ? ` · Routines ${completed}/${planned}` : '';
  return `${checkin}${mood}${routines}.`;
}

export function skillsSummary(input: {
  skillCount?: number | null;
  completion?: number | null;
  error?: boolean;
}): string | null {
  if (input.error) return null;
  if (typeof input.skillCount !== 'number') return null;
  if (input.skillCount <= 0) return 'No skills recorded yet.';
  const pct = typeof input.completion === 'number' ? ` · ${Math.round(input.completion)}% complete` : '';
  return `${input.skillCount} skill${input.skillCount === 1 ? '' : 's'}${pct}.`;
}

export function numberFromUnknown(value: unknown): number | null {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'string' && value.trim() && Number.isFinite(Number(value))) return Number(value);
  return null;
}
