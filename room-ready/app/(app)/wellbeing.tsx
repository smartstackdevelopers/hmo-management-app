import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getWellbeingDashboard } from '@/lib/hmore/services/wellbeing';

export default function WellbeingHubScreen() {
  const router = useRouter();
  const { t, fontScale } = useI18n();
  const query = useQuery({ queryKey: ['hmore', 'wellbeing-dashboard'], queryFn: getWellbeingDashboard });

  if (query.isLoading) return <LoadingScreen message={t('wellbeing.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const data = query.data ?? {};
  const progress = (data.routine_progress as Record<string, number> | undefined) ?? {};

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 24 * fontScale }]}>{t('wellbeing.title')}</Text>
      <Text style={styles.disclaimer}>{String(data.disclaimer ?? t('wellbeing.disclaimer'))}</Text>
      <Card style={styles.card}>
        <Text style={styles.meta}>
          {t('wellbeing.todayCheckin')}:{' '}
          {data.today_checkin ? t('wellbeing.done') : t('wellbeing.notDone')}
        </Text>
        <Text style={styles.meta}>
          {t('wellbeing.latestMood')}: {String(data.latest_mood ?? t('wellbeing.none'))}
        </Text>
        <Text style={styles.meta}>
          {t('wellbeing.routinesProgress')}: {progress.completed ?? 0}/{progress.planned ?? 0}
        </Text>
      </Card>
      <View style={styles.stack}>
        <Button title={t('wellbeing.checkin')} onPress={() => router.push('/(app)/wellbeing-checkin')} />
        <Button title={t('wellbeing.history')} variant="secondary" onPress={() => router.push('/(app)/wellbeing-history')} />
        <Button title={t('wellbeing.routines')} variant="secondary" onPress={() => router.push('/(app)/wellbeing-routines')} />
        <Button title={t('wellbeing.exercise')} variant="secondary" onPress={() => router.push('/(app)/wellbeing-exercise')} />
        <Button title={t('wellbeing.mindfulness')} variant="secondary" onPress={() => router.push('/(app)/wellbeing-mindfulness')} />
        <Button title={t('wellbeing.directory')} variant="secondary" onPress={() => router.push('/(app)/wellbeing-directory')} />
        <Button title={t('wellbeing.navigator')} variant="secondary" onPress={() => router.push('/(app)/wellbeing-navigator')} />
        <Button title={t('communityHub.title')} variant="secondary" onPress={() => router.push('/(app)/community-hub')} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  disclaimer: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 20, marginBottom: theme.spacing.md, fontSize: 12 },
  card: { marginBottom: theme.spacing.md, gap: 6 },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.text },
  stack: { gap: 10 },
});
