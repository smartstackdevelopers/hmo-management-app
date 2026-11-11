import { useRouter } from 'expo-router';
import { useQuery } from '@tanstack/react-query';
import { Pressable, StyleSheet, Text } from 'react-native';

import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listSavedMatchedJobs } from '@/lib/hmore/services/jobMatching';

export default function JobMatchingSavedScreen() {
  const { t, fontScale } = useI18n();
  const router = useRouter();
  const query = useQuery({ queryKey: ['hmore', 'job-matching-saved'], queryFn: listSavedMatchedJobs });
  if (query.isLoading) return <LoadingScreen message={t('jobMatching.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;
  const items = query.data?.items ?? [];
  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('jobMatching.saved')}</Text>
      {items.length === 0 ? (
        <Text style={styles.empty}>{t('jobMatching.noSaved')}</Text>
      ) : (
        items.map((item) => (
          <Pressable key={String(item.id)} onPress={() => router.push(`/(app)/job-matching-detail/${item.id}`)}>
            <Card style={styles.card}>
              <Text style={styles.name}>{String(item.title)}</Text>
              <Text style={styles.meta}>{String(item.employer_name)}</Text>
            </Card>
          </Pressable>
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.sm },
  card: { marginTop: theme.spacing.sm },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 4 },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: theme.spacing.md },
});
