/**
 * Non-clinical mood chart helpers for wellbeing history.
 * Mood values are display rankings only — never diagnoses.
 */

export const MOOD_RANK: Record<string, number> = {
  very_low: 1,
  low: 2,
  okay: 3,
  good: 4,
  very_good: 5,
};

export type HistoryPoint = {
  date: string;
  mood: string | null;
  skipped?: boolean;
  energy_level?: number | null;
  stress_level?: number | null;
};

export function moodRank(mood: string | null | undefined): number | null {
  if (!mood) return null;
  return MOOD_RANK[mood] ?? null;
}

export function buildMoodBars(
  items: HistoryPoint[],
): Array<{ date: string; rank: number; label: string }> {
  return items
    .filter((item) => !item.skipped && moodRank(item.mood) != null)
    .map((item) => ({
      date: item.date,
      rank: moodRank(item.mood) as number,
      label: String(item.mood).replace(/_/g, ' '),
    }))
    .reverse();
}

export function historyRangeDays(range: 'week' | 'month'): number {
  return range === 'week' ? 7 : 30;
}
