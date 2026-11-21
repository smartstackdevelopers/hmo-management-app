import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { FilterChips } from '@/components/dashboard/mobileChrome';
import { StatusRow, statusTone } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { buildMoodBars, historyRangeDays } from '@/lib/hmore/wellbeingHistoryChart';
import { deleteCheckin, listCheckins } from '@/lib/hmore/services/wellbeing';

export default function WellbeingHistoryScreen() {
  const { t, fontScale } = useI18n();
  const queryClient = useQueryClient();
  const [range, setRange] = useState<'week' | 'month'>('week');
  const days = historyRangeDays(range);
  const query = useQuery({
    queryKey: ['hmore', 'wellbeing-history', days],
    queryFn: () => listCheckins({ days, page_size: 50 }),
  });
  const remove = useMutation({
    mutationFn: (id: string) => deleteCheckin(id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'wellbeing-history'] });
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'wellbeing-dashboard'] });
    },
  });

  if (query.isLoading) return <LoadingScreen message={t('wellbeing.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const items = query.data?.items ?? [];
  const bars = buildMoodBars(
    items.map((item) => ({
      date: String(item.checkin_date ?? ''),
      mood: item.mood == null ? null : String(item.mood),
      skipped: Boolean(item.skipped),
    })),
  );

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('wellbeing.history')}</Text>
      <Text style={styles.disclaimer}>{query.data?.disclaimer}</Text>
      <Text style={styles.chartNote}>{t('wellbeing.chartNote')}</Text>
      <FilterChips
        value={range}
        onChange={(id) => setRange(id as 'week' | 'month')}
        options={[
          { id: 'week', label: t('wellbeing.week') },
          { id: 'month', label: t('wellbeing.month') },
        ]}
      />

      {bars.length ? (
        <Card style={styles.chartCard}>
          <Text style={styles.chartTitle}>{t('wellbeing.moodChart')}</Text>
          <View style={styles.chart}>
            {bars.map((bar) => (
              <View key={`${bar.date}-${bar.label}`} style={styles.barCol}>
                <View style={[styles.bar, { height: 12 + bar.rank * 14 }]} />
                <Text style={styles.barLabel}>{bar.date.slice(5)}</Text>
              </View>
            ))}
          </View>
        </Card>
      ) : null}

      {items.length === 0 ? (
        <Text style={styles.empty}>{t('wellbeing.noHistory')}</Text>
      ) : (
        items.map((item) => {
          const mood = item.skipped ? t('wellbeing.skipped') : String(item.mood ?? t('wellbeing.none')).replaceAll('_', ' ');
          const detail = item.skipped
            ? t('wellbeing.skipped')
            : [
                item.energy_level != null ? `${t('wellbeing.energy')} ${String(item.energy_level)}` : null,
                item.stress_level != null ? `${t('wellbeing.stress')} ${String(item.stress_level)}` : null,
                item.notes ? String(item.notes) : null,
              ].filter(Boolean).join(' · ');
          return (
            <View key={String(item.id)}>
              <StatusRow
                name={String(item.checkin_date)}
                title={String(item.checkin_date)}
                subtitle={detail || undefined}
                chip={mood}
                tone={item.skipped ? 'gray' : statusTone(String(item.mood ?? ''))}
              />
              <Button
                title={t('wellbeing.deleteCheckin')}
                variant="ghost"
                onPress={() => remove.mutate(String(item.id))}
              />
            </View>
          );
        })
      )}
      {remove.error ? <Text style={styles.error}>{hmoreErrorMessage(remove.error)}</Text> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  disclaimer: {
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    fontSize: 12,
    marginBottom: theme.spacing.sm,
  },
  chartNote: {
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textMuted,
    fontSize: 12,
    marginBottom: theme.spacing.sm,
  },
  chips: { flexDirection: 'row', gap: 8, marginBottom: theme.spacing.md },
  chip: { borderWidth: 1, borderColor: theme.colors.border, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8 },
  chipOn: { backgroundColor: theme.colors.text, borderColor: theme.colors.text },
  chipText: { fontFamily: FONT_MEDIUM, color: theme.colors.text },
  chipTextOn: { color: theme.colors.background },
  chartCard: { marginBottom: theme.spacing.md },
  chartTitle: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: 10 },
  chart: { flexDirection: 'row', alignItems: 'flex-end', gap: 6, minHeight: 90 },
  barCol: { alignItems: 'center', flex: 1, maxWidth: 36 },
  bar: { width: 14, borderRadius: 4, backgroundColor: theme.colors.secondary },
  barLabel: { fontFamily: FONT_MEDIUM, fontSize: 9, color: theme.colors.textMuted, marginTop: 4 },
  card: { marginBottom: theme.spacing.sm, gap: 6 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  error: { fontFamily: FONT_MEDIUM, color: theme.colors.danger, marginTop: 8 },
});
