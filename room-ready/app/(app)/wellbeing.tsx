import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { StyleSheet, Text } from 'react-native';

import { TileGrid } from '@/components/staff/ui';
import { HeroCard } from '@/components/ui/HeroCard';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getWellbeingDashboard } from '@/lib/hmore/services/wellbeing';

const TILES: {
  key: string;
  labelKey:
    | 'wellbeing.routines'
    | 'wellbeing.mindfulness'
    | 'wellbeing.exercise'
    | 'wellbeing.directory'
    | 'wellbeing.history'
    | 'wellbeing.navigator';
  href:
    | '/(app)/wellbeing-routines'
    | '/(app)/wellbeing-mindfulness'
    | '/(app)/wellbeing-exercise'
    | '/(app)/wellbeing-directory'
    | '/(app)/wellbeing-history'
    | '/(app)/wellbeing-navigator';
}[] = [
  { key: 'routines', labelKey: 'wellbeing.routines', href: '/(app)/wellbeing-routines' },
  { key: 'mind', labelKey: 'wellbeing.mindfulness', href: '/(app)/wellbeing-mindfulness' },
  { key: 'exercise', labelKey: 'wellbeing.exercise', href: '/(app)/wellbeing-exercise' },
  { key: 'local', labelKey: 'wellbeing.directory', href: '/(app)/wellbeing-directory' },
  { key: 'history', labelKey: 'wellbeing.history', href: '/(app)/wellbeing-history' },
  { key: 'nav', labelKey: 'wellbeing.navigator', href: '/(app)/wellbeing-navigator' },
];

export default function WellbeingHubScreen() {
  const router = useRouter();
  const { t, fontScale } = useI18n();
  const query = useQuery({ queryKey: ['hmore', 'wellbeing-dashboard'], queryFn: getWellbeingDashboard });

  if (query.isLoading) return <LoadingScreen message={t('wellbeing.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const data = query.data ?? {};
  const progress = (data.routine_progress as Record<string, number> | undefined) ?? {};
  const mood = data.latest_mood != null ? String(data.latest_mood).replace(/_/g, ' ') : null;
  const checkin = data.today_checkin ? t('wellbeing.done') : t('wellbeing.notDone');
  const routineLine = typeof progress.planned === 'number'
    ? `${t('wellbeing.routinesProgress')}: ${progress.completed ?? 0}/${progress.planned}`
    : null;
  const subtitle = [mood ? `${t('wellbeing.latestMood')}: ${mood}` : null, routineLine].filter(Boolean).join(' · ')
    || t('wellbeing.moodOptional');

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 28 * fontScale }]} accessibilityRole="header">{t('wellbeing.title')}</Text>
      <Text style={styles.disclaimer}>{String(data.disclaimer ?? t('wellbeing.disclaimer'))}</Text>
      <HeroCard
        kicker={t('wellbeing.checkin')}
        title={checkin}
        subtitle={subtitle}
        ctaLabel={t('wellbeing.checkin')}
        onCta={() => router.push('/(app)/wellbeing-checkin')}
      />
      <TileGrid
        tiles={TILES.map((tile) => ({
          key: tile.key,
          title: t(tile.labelKey),
          subtitle: tile.key === 'routines'
            ? routineLine
            : tile.key === 'history'
              ? mood
              : null,
          onPress: () => router.push(tile.href),
        }))}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.xs },
  disclaimer: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 20, marginBottom: theme.spacing.md, fontSize: 12 },
});
