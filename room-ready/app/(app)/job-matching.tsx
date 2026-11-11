import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { listJobSources } from '@/lib/hmore/services/jobMatching';

export default function JobMatchingHubScreen() {
  const router = useRouter();
  const { t, fontScale } = useI18n();
  const sources = useQuery({ queryKey: ['hmore', 'job-matching-sources'], queryFn: listJobSources });
  const sourceRows = sources.data?.sources ?? [];

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 24 * fontScale }]}>{t('jobMatching.title')}</Text>
      <Text style={styles.lead}>{t('jobMatching.lead')}</Text>
      <Card style={styles.card}>
        <Text style={styles.meta}>{t('jobMatching.sourcesStatus')}</Text>
        {sourceRows.length === 0 ? (
          <Text style={styles.meta}>{t('jobMatching.sourcesLoading')}</Text>
        ) : (
          sourceRows.map((row) => (
            <Text key={String(row.source)} style={styles.meta}>
              {String(row.source)}: {row.available ? t('jobMatching.sourceReady') : String(row.detail ?? t('jobMatching.sourceMissing'))}
            </Text>
          ))
        )}
        <Text style={styles.meta}>{t('jobMatching.sourcesFallback')}</Text>
      </Card>
      <View style={styles.stack}>
        <Button title={t('jobMatching.recommended')} onPress={() => router.push('/(app)/job-matching-recommended')} />
        <Button title={t('jobMatching.search')} variant="secondary" onPress={() => router.push('/(app)/job-matching-search')} />
        <Button title={t('jobMatching.saved')} variant="secondary" onPress={() => router.push('/(app)/job-matching-saved')} />
        <Button title={t('jobMatching.training')} variant="secondary" onPress={() => router.push('/(app)/job-matching-training')} />
        <Button title={t('jobMatching.preferences')} variant="secondary" onPress={() => router.push('/(app)/job-matching-preferences')} />
        <Button title={t('employment.applications')} variant="secondary" onPress={() => router.push('/(app)/employment-applications')} />
        <Button title={t('communityHub.title')} variant="secondary" onPress={() => router.push('/(app)/community-hub')} />
      </View>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  lead: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 22, marginBottom: theme.spacing.md },
  card: { marginBottom: theme.spacing.md, gap: 4 },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 13, lineHeight: 18 },
  stack: { gap: 10 },
});
