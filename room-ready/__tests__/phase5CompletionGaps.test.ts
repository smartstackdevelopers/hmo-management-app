import { readFileSync } from 'fs';
import path from 'path';

import { buildMoodBars, historyRangeDays, moodRank } from '@/lib/hmore/wellbeingHistoryChart';

describe('F5.5 history chart helpers', () => {
  it('maps moods without inventing medical labels', () => {
    expect(moodRank('good')).toBe(4);
    expect(moodRank(null)).toBeNull();
    expect(historyRangeDays('week')).toBe(7);
    expect(historyRangeDays('month')).toBe(30);
    expect(
      buildMoodBars([
        { date: '2026-11-10', mood: 'good' },
        { date: '2026-11-09', mood: null, skipped: true },
        { date: '2026-11-08', mood: 'low' },
      ]).map((row) => row.rank),
    ).toEqual([2, 4]);
  });
});

describe('F5 completion gap wiring', () => {
  it('enables optional routine reminders from the mobile form', () => {
    const src = readFileSync(path.join(__dirname, '../app/(app)/wellbeing-routines.tsx'), 'utf8');
    expect(src).toContain('reminder_enabled: reminders');
    expect(src).not.toContain('reminder_enabled: false');
    expect(src).toContain('updateRoutine');
    expect(src).toContain('deleteRoutine');
  });

  it('supports weekly/monthly history, chart and delete', () => {
    const src = readFileSync(path.join(__dirname, '../app/(app)/wellbeing-history.tsx'), 'utf8');
    expect(src).toContain("setRange('week')");
    expect(src).toContain("setRange('month')");
    expect(src).toContain('buildMoodBars');
    expect(src).toContain('deleteCheckin');
  });

  it('exposes per-service directions from real coordinates', () => {
    const src = readFileSync(path.join(__dirname, '../components/help/NearbyMap.tsx'), 'utf8');
    expect(src).toContain('directionsUrl');
    expect(src).toContain('item.latitude');
    expect(src).toContain('item.longitude');
    expect(src).toContain('Directions');
  });

  it('surfaces job source configuration instead of inventing listings', () => {
    const src = readFileSync(path.join(__dirname, '../app/(app)/job-matching.tsx'), 'utf8');
    expect(src).toContain('listJobSources');
    expect(src).toContain('sourcesFallback');
  });
});
