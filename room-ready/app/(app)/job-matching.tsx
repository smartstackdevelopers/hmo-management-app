import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { StyleSheet, Text } from 'react-native';

import { TileGrid } from '@/components/staff/ui';
import { Card } from '@/components/ui/Card';
import { HeroCard } from '@/components/ui/HeroCard';
import { ListRow } from '@/components/ui/ListRow';
import { Screen } from '@/components/ui/Screen';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { listJobSources } from '@/lib/hmore/services/jobMatching';

const TILES: {
  key: string;
  labelKey: 'jobMatching.recommended' | 'jobMatching.search' | 'jobMatching.saved' | 'jobMatching.training' | 'jobMatching.preferences' | 'employment.applications';
  href: '/(app)/job-matching-recommended' | '/(app)/job-matching-search' | '/(app)/job-matching-saved' | '/(app)/job-matching-training' | '/(app)/job-matching-preferences' | '/(app)/employment-applications';
}[] = [
  { key: 'recommended', labelKey: 'jobMatching.recommended', href: '/(app)/job-matching-recommended' },
  { key: 'search', labelKey: 'jobMatching.search', href: '/(app)/job-matching-search' },
  { key: 'saved', labelKey: 'jobMatching.saved', href: '/(app)/job-matching-saved' },
  { key: 'training', labelKey: 'jobMatching.training', href: '/(app)/job-matching-training' },
  { key: 'prefs', labelKey: 'jobMatching.preferences', href: '/(app)/job-matching-preferences' },
  { key: 'apps', labelKey: 'employment.applications', href: '/(app)/employment-applications' },
];

export default function JobMatchingHubScreen() {
  const router = useRouter();
  const { t, fontScale } = useI18n();
  const sources = useQuery({ queryKey: ['hmore', 'job-matching-sources'], queryFn: listJobSources });
  const sourceRows = sources.data?.sources ?? [];

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 28 * fontScale }]}>{t('jobMatching.title')}</Text>
      <Text style={styles.lead}>{t('jobMatching.lead')}</Text>
      <HeroCard
        kicker={t('jobMatching.recommended')}
        title={t('jobMatching.title')}
        subtitle={t('jobMatching.lead')}
        icon="search"
        ctaLabel={t('jobMatching.search')}
        onCta={() => router.push('/(app)/job-matching-search')}
      />
      <TileGrid
        tiles={TILES.map((tile) => ({
          key: tile.key,
          title: t(tile.labelKey),
          onPress: () => router.push(tile.href),
        }))}
      />
      <Text style={styles.section}>{t('jobMatching.sourcesStatus')}</Text>
      <Card padded={false} style={styles.sources}>
        {sourceRows.length === 0 ? (
          <ListRow title={t('jobMatching.sourcesLoading')} icon="cloud-outline" />
        ) : (
          sourceRows.map((row, index) => (
            <ListRow
              key={String(row.source)}
              title={String(row.source)}
              subtitle={row.available ? t('jobMatching.sourceReady') : String(row.detail ?? t('jobMatching.sourceMissing'))}
              icon="cloud-outline"
              tone={row.available ? 'green' : 'amber'}
              chipLabel={row.available ? t('jobMatching.sourceReady') : t('jobMatching.sourceMissing')}
              chipTone={row.available ? 'green' : 'amber'}
              divider={index < sourceRows.length - 1}
            />
          ))
        )}
      </Card>
      <Text style={styles.note}>{t('jobMatching.sourcesFallback')}</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.xs },
  lead: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 22, marginBottom: theme.spacing.md },
  grid: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'space-between', rowGap: 10, marginBottom: theme.spacing.md },
  tile: { width: '48%', minHeight: 112 },
  tileTitle: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text, marginTop: 10 },
  section: { fontFamily: FONT_BOLD, fontSize: 17, color: theme.colors.text, marginBottom: 10 },
  sources: { marginBottom: theme.spacing.sm },
  note: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 13, lineHeight: 18 },
});
