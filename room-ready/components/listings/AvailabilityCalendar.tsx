import { StyleSheet, Text, View } from 'react-native';

import { theme } from '@/constants/theme';

interface AvailabilityCalendarProps {
  availableFrom?: string;
  weeks?: number;
}

export function AvailabilityCalendar({ availableFrom, weeks = 8 }: AvailabilityCalendarProps) {
  const start = availableFrom ? new Date(availableFrom) : new Date();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const days: { date: Date; status: 'available' | 'blocked' | 'today' }[] = [];
  for (let i = 0; i < weeks * 7; i++) {
    const date = new Date(start);
    date.setDate(start.getDate() + i);
    const blocked = date < today || (availableFrom && date < new Date(availableFrom));
    const isToday = date.toDateString() === today.toDateString();
    days.push({
      date,
      status: isToday ? 'today' : blocked ? 'blocked' : 'available',
    });
  }

  const monthLabel = start.toLocaleDateString('en-GB', { month: 'long', year: 'numeric' });

  return (
    <View style={styles.wrap}>
      <Text style={styles.month}>{monthLabel} onwards</Text>
      <View style={styles.grid}>
        {days.map((day) => (
          <View
            key={day.date.toISOString()}
            style={[
              styles.cell,
              day.status === 'available' && styles.available,
              day.status === 'blocked' && styles.blocked,
              day.status === 'today' && styles.today,
            ]}
          >
            <Text style={[styles.dayNum, day.status === 'blocked' && styles.dayNumMuted]}>
              {day.date.getDate()}
            </Text>
          </View>
        ))}
      </View>
      <View style={styles.legend}>
        <LegendDot color={theme.colors.success} label="Available" />
        <LegendDot color={theme.colors.border} label="Unavailable" />
        <LegendDot color={theme.colors.secondary} label="Today" />
      </View>
    </View>
  );
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <View style={styles.legendItem}>
      <View style={[styles.dot, { backgroundColor: color }]} />
      <Text style={styles.legendText}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { gap: 10 },
  month: { fontWeight: '600', color: theme.colors.text, fontSize: 14 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 },
  cell: {
    width: 36,
    height: 36,
    borderRadius: theme.radius.sm,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: theme.colors.borderLight,
  },
  available: { backgroundColor: theme.colors.successLight, borderColor: theme.colors.success },
  blocked: { backgroundColor: theme.colors.surfaceSecondary },
  today: { backgroundColor: theme.colors.infoLight, borderColor: theme.colors.secondary, borderWidth: 2 },
  dayNum: { fontSize: 12, fontWeight: '600', color: theme.colors.text },
  dayNumMuted: { color: theme.colors.textMuted },
  legend: { flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginTop: 4 },
  legendItem: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  dot: { width: 10, height: 10, borderRadius: 5 },
  legendText: { fontSize: 12, color: theme.colors.textMuted },
});
