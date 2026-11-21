import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { StyleSheet, Text } from 'react-native';

import { StatusRow } from '@/components/staff/ui';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { recommendedJobs } from '@/lib/hmore/services/jobMatching';

export default function JobMatchingRecommendedScreen() {
  const { t, fontScale } = useI18n();
  const router = useRouter();
  const query = useQuery({ queryKey: ['hmore', 'job-matching-recommended'], queryFn: recommendedJobs });
  if (query.isLoading) return <LoadingScreen message={t('jobMatching.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;
  const items = query.data?.items ?? [];
  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('jobMatching.recommended')}</Text>
      {items.length === 0 ? (
        <Text style={styles.empty}>{t('jobMatching.empty')}</Text>
      ) : (
        items.map((item) => (
          <StatusRow
            key={String(item.id)}
            name={String(item.title)}
            title={String(item.title)}
            subtitle={[String(item.employer_name || ''), item.location ? String(item.location) : null].filter(Boolean).join(' · ')}
            chip={item.score != null ? String(item.score) : undefined}
            tone="green"
            onPress={() => router.push(`/(app)/job-matching-detail/${item.id}`)}
          />
        ))
      )}
      <Text style={styles.disclaimer}>{query.data?.disclaimer}</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.sm },
  card: { marginTop: theme.spacing.sm },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: theme.spacing.md },
  disclaimer: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: theme.spacing.lg, fontSize: 12 },
});
