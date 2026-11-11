import { useQuery } from '@tanstack/react-query';
import { StyleSheet, Text } from 'react-native';

import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listCheckins } from '@/lib/hmore/services/wellbeing';

export default function WellbeingHistoryScreen() {
  const { t, fontScale } = useI18n();
  const query = useQuery({
    queryKey: ['hmore', 'wellbeing-history'],
    queryFn: () => listCheckins({ days: 30 }),
  });
  if (query.isLoading) return <LoadingScreen message={t('wellbeing.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;
  const items = query.data?.items ?? [];
  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('wellbeing.history')}</Text>
      <Text style={styles.disclaimer}>{query.data?.disclaimer}</Text>
      {items.length === 0 ? (
        <Text style={styles.empty}>{t('wellbeing.noHistory')}</Text>
      ) : (
        items.map((item) => (
          <Card key={String(item.id)} style={styles.card}>
            <Text style={styles.name}>{String(item.checkin_date)}</Text>
            <Text style={styles.meta}>
              {item.skipped
                ? t('wellbeing.skipped')
                : `${t('wellbeing.mood')}: ${String(item.mood ?? '—')} · ${t('wellbeing.energy')}: ${String(item.energy_level ?? '—')} · ${t('wellbeing.stress')}: ${String(item.stress_level ?? '—')}`}
            </Text>
            {item.notes ? <Text style={styles.body}>{String(item.notes)}</Text> : null}
          </Card>
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  disclaimer: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 12, marginBottom: theme.spacing.md },
  card: { marginBottom: theme.spacing.sm, gap: 4 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
});
