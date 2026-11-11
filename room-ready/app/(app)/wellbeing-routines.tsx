import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { createRoutine, listRoutines, setRoutineStatus } from '@/lib/hmore/services/wellbeing';

export default function WellbeingRoutinesScreen() {
  const { t, fontScale } = useI18n();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [start, setStart] = useState('08:00');
  const query = useQuery({ queryKey: ['hmore', 'wellbeing-routines'], queryFn: () => listRoutines() });

  const create = useMutation({
    mutationFn: () =>
      createRoutine({
        title: title.trim(),
        category: 'other',
        start_time: `${start}:00`.slice(0, 8),
        recurrence: 'daily',
        reminder_enabled: false,
      }),
    onSuccess: async () => {
      setTitle('');
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'wellbeing-routines'] });
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'wellbeing-dashboard'] });
    },
  });

  const mark = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'completed' | 'skipped' }) =>
      setRoutineStatus(id, { status }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'wellbeing-routines'] });
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'wellbeing-dashboard'] });
    },
  });

  if (query.isLoading) return <LoadingScreen message={t('wellbeing.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const items = query.data?.items ?? [];
  const progress = query.data?.progress ?? {};

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('wellbeing.routines')}</Text>
      <Text style={styles.meta}>{query.data?.note}</Text>
      <Text style={styles.meta}>
        {t('wellbeing.routinesProgress')}: {progress.completed ?? 0}/{progress.planned ?? 0}
      </Text>
      <Input label={t('wellbeing.routineTitle')} value={title} onChangeText={setTitle} />
      <Input label={t('wellbeing.startTime')} value={start} onChangeText={setStart} placeholder="08:00" />
      <Button title={t('wellbeing.addRoutine')} onPress={() => create.mutate()} />
      {items.map((item) => (
        <Card key={String(item.id)} style={styles.card}>
          <Text style={styles.name}>{String(item.title)}</Text>
          <Text style={styles.meta}>
            {String(item.start_time)} · {String(item.today_status ?? t('wellbeing.pending'))}
          </Text>
          <View style={styles.row}>
            <Button title={t('wellbeing.complete')} onPress={() => mark.mutate({ id: String(item.id), status: 'completed' })} />
            <Button
              title={t('wellbeing.skip')}
              variant="secondary"
              onPress={() => mark.mutate({ id: String(item.id), status: 'skipped' })}
            />
          </View>
        </Card>
      ))}
      {create.error || mark.error ? (
        <Text style={styles.error}>{hmoreErrorMessage(create.error || mark.error)}</Text>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: 6 },
  card: { marginTop: theme.spacing.sm, gap: 8 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  row: { gap: 8 },
  error: { fontFamily: FONT_MEDIUM, color: theme.colors.danger, marginTop: 8 },
});
