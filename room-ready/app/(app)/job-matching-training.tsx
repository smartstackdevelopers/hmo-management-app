import { useQuery } from '@tanstack/react-query';
import { Linking, StyleSheet, Text } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listTrainingRecommendations } from '@/lib/hmore/services/jobMatching';

export default function JobMatchingTrainingScreen() {
  const { t, fontScale } = useI18n();
  const query = useQuery({ queryKey: ['hmore', 'job-matching-training'], queryFn: listTrainingRecommendations });
  if (query.isLoading) return <LoadingScreen message={t('jobMatching.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;
  const items = query.data?.items ?? [];
  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('jobMatching.training')}</Text>
      <Text style={styles.meta}>{query.data?.disclaimer}</Text>
      {items.length === 0 ? (
        <Text style={styles.empty}>{t('jobMatching.noTraining')}</Text>
      ) : (
        items.map((item) => (
          <Card key={String(item.id)} style={styles.card}>
            <Text style={styles.name}>{String(item.title)}</Text>
            <Text style={styles.meta}>
              {String(item.provider_name)} · {String(item.verification_status)}
              {item.is_free_verified ? ` · ${t('jobMatching.freeVerified')}` : ''}
            </Text>
            {Array.isArray(item.reasons)
              ? item.reasons.map((reason) => (
                  <Text key={String(reason)} style={styles.body}>
                    • {String(reason)}
                  </Text>
                ))
              : null}
            {item.source_url ? (
              <Button
                title={t('jobMatching.openSource')}
                variant="secondary"
                onPress={() => Linking.openURL(String(item.source_url))}
              />
            ) : null}
          </Card>
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.sm },
  card: { marginTop: theme.spacing.sm, gap: 6 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: theme.spacing.md },
});
