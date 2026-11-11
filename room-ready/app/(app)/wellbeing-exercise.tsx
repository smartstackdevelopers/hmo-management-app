import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { StyleSheet, Text } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { completeResource, listResources, saveResource } from '@/lib/hmore/services/wellbeing';

export default function WellbeingExerciseScreen() {
  const { t, fontScale } = useI18n();
  const queryClient = useQueryClient();
  const query = useQuery({
    queryKey: ['hmore', 'wellbeing-exercise'],
    queryFn: () => listResources({ kind: 'exercise' }),
  });
  const save = useMutation({
    mutationFn: (id: string) => saveResource(id),
    onSuccess: async () => queryClient.invalidateQueries({ queryKey: ['hmore', 'wellbeing-exercise'] }),
  });
  const complete = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'completed' | 'stopped' }) => completeResource(id, status),
  });

  if (query.isLoading) return <LoadingScreen message={t('wellbeing.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('wellbeing.exercise')}</Text>
      <Text style={styles.disclaimer}>{query.data?.disclaimer}</Text>
      {(query.data?.items ?? []).map((item) => (
        <Card key={String(item.id)} style={styles.card}>
          <Text style={styles.name}>{String(item.title)}</Text>
          <Text style={styles.meta}>
            {String(item.category)} · {String(item.duration_minutes ?? '—')} min · {String(item.activity_level ?? '')}
          </Text>
          {item.description ? <Text style={styles.body}>{String(item.description)}</Text> : null}
          {item.instructions ? <Text style={styles.body}>{String(item.instructions)}</Text> : null}
          {item.safety_notes ? <Text style={styles.meta}>{String(item.safety_notes)}</Text> : null}
          <Button title={t('wellbeing.saveResource')} onPress={() => save.mutate(String(item.id))} />
          <Button
            title={t('wellbeing.markCompleted')}
            variant="secondary"
            onPress={() => complete.mutate({ id: String(item.id), status: 'completed' })}
          />
          <Button
            title={t('wellbeing.stopActivity')}
            variant="secondary"
            onPress={() => complete.mutate({ id: String(item.id), status: 'stopped' })}
          />
        </Card>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  disclaimer: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 12, marginBottom: theme.spacing.md },
  card: { marginBottom: theme.spacing.sm, gap: 8 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text, lineHeight: 20 },
});
