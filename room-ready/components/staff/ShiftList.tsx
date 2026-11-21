import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Text } from 'react-native';

import { useHideTabHeader } from '@/components/dashboard/mobileChrome';
import { AgendaRow, StaffPage, WeekStrip, staffLabel, statusTone } from '@/components/staff/ui';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listCaseload } from '@/lib/hmore/services/staff/caseload';
import { listOwnShifts, type StaffShift } from '@/lib/hmore/services/staff/shifts';
import { listVisits, type StaffVisit } from '@/lib/hmore/services/staff/visits';

function startOfWeek(now = new Date()): Date {
  const day = now.getDay();
  const mondayOffset = day === 0 ? -6 : 1 - day;
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate() + mondayOffset);
  start.setHours(0, 0, 0, 0);
  return start;
}

function dayKey(date: Date): string {
  return `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`;
}

function sameDay(iso: string, day: Date): boolean {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return false;
  return date.getFullYear() === day.getFullYear() && date.getMonth() === day.getMonth() && date.getDate() === day.getDate();
}

function clock(iso: string | null | undefined): string | null {
  if (!iso) return null;
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return null;
  return date.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' });
}

function hoursInWeek(shifts: StaffShift[], start: Date): number | null {
  const end = new Date(start);
  end.setDate(end.getDate() + 7);
  let total = 0;
  let any = false;
  for (const shift of shifts) {
    const begins = new Date(shift.starts_at);
    const finishes = new Date(shift.ends_at);
    if (Number.isNaN(begins.getTime()) || Number.isNaN(finishes.getTime()) || finishes <= begins) continue;
    if (begins < start || begins >= end) continue;
    total += (finishes.getTime() - begins.getTime()) / 36e5;
    any = true;
  }
  return any ? Math.round(total * 10) / 10 : null;
}

type AgendaItem = {
  key: string;
  time: string | null;
  title: string;
  subtitle: string;
  tone: ReturnType<typeof statusTone>;
  sort: number;
  onPress?: () => void;
};

export function ShiftList() {
  useHideTabHeader();
  const { user } = useAuth();
  const weekStart = useMemo(() => startOfWeek(), []);
  const days = useMemo(
    () =>
      Array.from({ length: 7 }, (_, index) => {
        const date = new Date(weekStart);
        date.setDate(weekStart.getDate() + index);
        return date;
      }),
    [weekStart],
  );
  const [selectedKey, setSelectedKey] = useState(() => dayKey(new Date()));
  const shifts = useQuery({
    queryKey: ['hmore', 'staff', 'shifts', user?.id],
    queryFn: () => listOwnShifts(user?.id || ''),
    enabled: !!user?.id,
  });
  const visits = useQuery({
    queryKey: ['hmore', 'staff', 'visits'],
    queryFn: () => listVisits(),
  });
  const caseload = useQuery({
    queryKey: ['hmore', 'staff', 'caseload', user?.role],
    queryFn: () => listCaseload(user?.role, { page: 1, page_size: 50, status: 'active' }),
  });

  if (shifts.isLoading) return <LoadingScreen message="Loading shifts..." />;
  if (shifts.isError) return <ErrorState message={hmoreErrorMessage(shifts.error, 'Could not load shifts')} onRetry={shifts.refetch} />;

  const shiftItems = shifts.data?.items ?? [];
  const visitItems = visits.data?.items ?? [];
  const names = new Map(
    (caseload.data?.items ?? []).map((row) => [row.tenant_id, row.tenant_preferred_name || row.tenant_full_name || '']),
  );
  const selected = days.find((day) => dayKey(day) === selectedKey) ?? days.find((day) => dayKey(day) === dayKey(new Date())) ?? days[0];
  const hours = hoursInWeek(shiftItems, weekStart);
  const weekCount = shiftItems.filter((shift) => {
    const begins = new Date(shift.starts_at);
    const end = new Date(weekStart);
    end.setDate(end.getDate() + 7);
    return !Number.isNaN(begins.getTime()) && begins >= weekStart && begins < end;
  }).length;
  const subtitle = hours != null ? `This week · ${hours}h scheduled` : `This week · ${weekCount} scheduled`;

  const agenda: AgendaItem[] = [
    ...shiftItems.filter((shift) => sameDay(shift.starts_at, selected)).map((shift) => shiftRow(shift)),
    ...visitItems.filter((visit) => sameDay(visit.scheduled_at, selected)).map((visit) => visitRow(visit, names)),
  ].sort((a, b) => a.sort - b.sort);

  return (
    <StaffPage
      title="Shifts"
      subtitle={subtitle}
      onRefresh={() => {
        shifts.refetch();
        visits.refetch();
      }}
      refreshing={shifts.isRefetching || visits.isRefetching}
    >
      <WeekStrip
        selectedKey={dayKey(selected)}
        onSelect={setSelectedKey}
        days={days.map((day) => ({
          key: dayKey(day),
          weekday: day.toLocaleDateString('en-GB', { weekday: 'narrow' }),
          day: String(day.getDate()),
          marked:
            shiftItems.some((shift) => sameDay(shift.starts_at, day)) ||
            visitItems.some((visit) => sameDay(visit.scheduled_at, day)),
        }))}
      />
      {agenda.length === 0 ? (
        <Text style={{ fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 20 }}>
          Nothing is scheduled on this day.
        </Text>
      ) : (
        agenda.map((item) => (
          <AgendaRow
            key={item.key}
            time={item.time}
            title={item.title}
            subtitle={item.subtitle}
            tone={item.tone}
            onPress={item.onPress}
          />
        ))
      )}
    </StaffPage>
  );
}

function minutesBetween(start: string, end: string | null | undefined): string | null {
  if (!end) return null;
  const begins = new Date(start).getTime();
  const finishes = new Date(end).getTime();
  if (Number.isNaN(begins) || Number.isNaN(finishes) || finishes <= begins) return null;
  const mins = Math.round((finishes - begins) / 60000);
  if (mins < 60) return `${mins} min`;
  const hours = Math.round((mins / 60) * 10) / 10;
  return `${hours}h`;
}

function shiftRow(shift: StaffShift): AgendaItem {
  return {
    key: `shift-${shift.id}`,
    time: clock(shift.starts_at),
    title: staffLabel(shift.shift_type) || 'Shift',
    subtitle: [shift.location, minutesBetween(shift.starts_at, shift.ends_at)].filter(Boolean).join(' · '),
    tone: statusTone(shift.status),
    sort: new Date(shift.starts_at).getTime() || 0,
  };
}

function visitRow(visit: StaffVisit, names: Map<string, string>): AgendaItem {
  const who = names.get(visit.tenant_id) || visit.purpose || staffLabel(visit.visit_type);
  return {
    key: `visit-${visit.id}`,
    time: clock(visit.scheduled_at),
    title: who,
    subtitle: visit.location || staffLabel(visit.visit_type),
    tone: statusTone(visit.status),
    sort: new Date(visit.scheduled_at).getTime() || 0,
    onPress: () => router.push(`/(app)/staff/visits?visitId=${visit.id}`),
  };
}
