import { useLocalSearchParams, useRouter } from 'expo-router';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Linking, StyleSheet, Text } from 'react-native';
import { useState } from 'react';

import { Button } from '@/components/ui/Button';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import {
  addMatchedJobToTracker,
  explainJobMatch,
  getMatchedJob,
  saveMatchedJob,
} from '@/lib/hmore/services/jobMatching';

export default function JobMatchingDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t, fontScale } = useI18n();
  const router = useRouter();
  const queryClient = useQueryClient();
  const [message, setMessage] = useState<string | null>(null);
  const [explanation, setExplanation] = useState<string | null>(null);
  const query = useQuery({
    queryKey: ['hmore', 'job-matching-detail', id],
    queryFn: () => getMatchedJob(String(id)),
    enabled: Boolean(id),
  });

  const save = useMutation({
    mutationFn: () => saveMatchedJob(String(id)),
    onSuccess: async () => {
      setMessage(t('jobMatching.savedOk'));
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'job-matching-saved'] });
    },
  });
  const track = useMutation({
    mutationFn: () => addMatchedJobToTracker({ job_id: String(id), status: 'interested' }),
    onSuccess: () => {
      setMessage(t('jobMatching.tracked'));
      router.push('/(app)/employment-applications');
    },
  });
  const explain = useMutation({
    mutationFn: () => explainJobMatch({ job_id: String(id) }),
    onSuccess: (data) => setExplanation(String(data.explanation ?? '')),
  });

  if (query.isLoading) return <LoadingScreen message={t('jobMatching.loading')} />;
  if (query.error || !query.data) {
    return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;
  }
  const job = query.data;
  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{String(job.title)}</Text>
      <Text style={styles.meta}>
        {String(job.employer_name)} · {String(job.location ?? '—')} · {String(job.source_name)}
      </Text>
      {job.score != null ? (
        <Text style={styles.meta}>
          {t('jobMatching.score')}: {String(job.score)}
        </Text>
      ) : null}
      {Array.isArray(job.reasons)
        ? job.reasons.map((reason) => (
            <Text key={String(reason)} style={styles.body}>
              • {String(reason)}
            </Text>
          ))
        : null}
      {Array.isArray(job.missing_skills) && job.missing_skills.length ? (
        <Text style={styles.meta}>
          {t('jobMatching.missingSkills')}: {job.missing_skills.map(String).join(', ')}
        </Text>
      ) : null}
      {job.description ? <Text style={styles.body}>{String(job.description).slice(0, 1200)}</Text> : null}
      <Button title={t('jobMatching.save')} onPress={() => save.mutate()} />
      <Button title={t('jobMatching.addTracker')} variant="secondary" onPress={() => track.mutate()} />
      <Button title={t('jobMatching.explain')} variant="secondary" onPress={() => explain.mutate()} />
      {job.source_url ? (
        <Button title={t('jobMatching.openSource')} variant="secondary" onPress={() => Linking.openURL(String(job.source_url))} />
      ) : null}
      {explanation ? <Text style={styles.body}>{explanation}</Text> : null}
      {message ? <Text style={styles.meta}>{message}</Text> : null}
      {save.error || track.error || explain.error ? (
        <Text style={styles.error}>
          {hmoreErrorMessage(save.error || track.error || explain.error)}
        </Text>
      ) : null}
      <Text style={styles.disclaimer}>{String(job.disclaimer ?? '')}</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: 6 },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text, marginBottom: 8, lineHeight: 22 },
  error: { fontFamily: FONT_MEDIUM, color: theme.colors.danger, marginTop: 8 },
  disclaimer: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: theme.spacing.lg, fontSize: 12 },
});
