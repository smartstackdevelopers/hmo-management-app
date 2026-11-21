import { useQuery } from '@tanstack/react-query';
import { Linking, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { ListRow } from '@/components/ui/ListRow';
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
          <Card key={String(item.id)} padded={false} style={styles.card}>
            <ListRow
              title={String(item.title)}
              subtitle={String(item.provider_name)}
              icon="school-outline"
              chipLabel={item.is_free_verified ? t('jobMatching.freeVerified') : String(item.verification_status).replaceAll('_', ' ')}
              chipTone={item.is_free_verified || item.verification_status === 'verified' ? 'green' : 'gray'}
              chevron={false}
            />
            <View style={styles.bodyWrap}>
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
            </View>
          </Card>
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.sm },
  card: { marginTop: theme.spacing.sm },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  bodyWrap: { paddingHorizontal: theme.spacing.md, paddingBottom: theme.spacing.md, gap: 6 },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: theme.spacing.md },
});
