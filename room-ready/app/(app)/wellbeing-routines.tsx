import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import {
  createRoutine,
  deleteRoutine,
  listRoutines,
  setRoutineStatus,
  updateRoutine,
} from '@/lib/hmore/services/wellbeing';

const CATEGORIES = [
  'morning',
  'personal_care',
  'exercise',
  'meals',
  'work_study',
  'family',
  'relaxation',
  'evening',
  'other',
] as const;

const RECURRENCE = ['daily', 'weekdays', 'weekly', 'one_time'] as const;

function toApiTime(value: string): string {
  const trimmed = value.trim();
  if (/^\d{2}:\d{2}:\d{2}$/.test(trimmed)) return trimmed;
  if (/^\d{2}:\d{2}$/.test(trimmed)) return `${trimmed}:00`;
  return '08:00:00';
}

export default function WellbeingRoutinesScreen() {
  const { t, fontScale } = useI18n();
  const queryClient = useQueryClient();
  const [title, setTitle] = useState('');
  const [start, setStart] = useState('08:00');
  const [end, setEnd] = useState('');
  const [category, setCategory] = useState<(typeof CATEGORIES)[number]>('other');
  const [recurrence, setRecurrence] = useState<(typeof RECURRENCE)[number]>('daily');
  const [reminders, setReminders] = useState(false);
  const [minutesBefore, setMinutesBefore] = useState('15');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const query = useQuery({ queryKey: ['hmore', 'wellbeing-routines'], queryFn: () => listRoutines() });

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['hmore', 'wellbeing-routines'] });
    await queryClient.invalidateQueries({ queryKey: ['hmore', 'wellbeing-dashboard'] });
  };

  const payload = () => ({
    title: title.trim(),
    category,
    start_time: toApiTime(start),
    end_time: end.trim() ? toApiTime(end) : null,
    recurrence,
    reminder_enabled: reminders,
    reminder_minutes_before: reminders ? Number(minutesBefore) || 15 : null,
  });

  const save = useMutation({
    mutationFn: () =>
      editingId ? updateRoutine(editingId, payload()) : createRoutine(payload()),
    onSuccess: async () => {
      setTitle('');
      setEnd('');
      setEditingId(null);
      setReminders(false);
      setMessage(t('wellbeing.saved'));
      await refresh();
    },
  });

  const mark = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'completed' | 'skipped' }) =>
      setRoutineStatus(id, { status }),
    onSuccess: async () => refresh(),
  });

  const remove = useMutation({
    mutationFn: (id: string) => deleteRoutine(id),
    onSuccess: async () => {
      if (editingId) setEditingId(null);
      await refresh();
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
      <Text style={styles.disclaimer}>{t('wellbeing.routineFlexible')}</Text>

      <Input label={t('wellbeing.routineTitle')} value={title} onChangeText={setTitle} />
      <Input label={t('wellbeing.startTime')} value={start} onChangeText={setStart} placeholder="08:00" />
      <Input label={t('wellbeing.endTime')} value={end} onChangeText={setEnd} placeholder="09:00" />

      <Text style={styles.label}>{t('wellbeing.category')}</Text>
      <View style={styles.chips}>
        {CATEGORIES.map((item) => (
          <Pressable
            key={item}
            onPress={() => setCategory(item)}
            style={[styles.chip, category === item && styles.chipOn]}
          >
            <Text style={[styles.chipText, category === item && styles.chipTextOn]}>
              {item.replaceAll('_', ' ')}
            </Text>
          </Pressable>
        ))}
      </View>

      <Text style={styles.label}>{t('wellbeing.recurrence')}</Text>
      <View style={styles.chips}>
        {RECURRENCE.map((item) => (
          <Pressable
            key={item}
            onPress={() => setRecurrence(item)}
            style={[styles.chip, recurrence === item && styles.chipOn]}
          >
            <Text style={[styles.chipText, recurrence === item && styles.chipTextOn]}>
              {item.replaceAll('_', ' ')}
            </Text>
          </Pressable>
        ))}
      </View>

      <Pressable
        onPress={() => setReminders((value) => !value)}
        style={[styles.chip, reminders && styles.chipOn, styles.remindChip]}
        accessibilityRole="switch"
        accessibilityState={{ checked: reminders }}
      >
        <Text style={[styles.chipText, reminders && styles.chipTextOn]}>
          {reminders ? t('wellbeing.remindersOn') : t('wellbeing.remindersOff')}
        </Text>
      </Pressable>
      {reminders ? (
        <Input
          label={t('wellbeing.reminderMinutes')}
          value={minutesBefore}
          onChangeText={setMinutesBefore}
          keyboardType="number-pad"
        />
      ) : null}

      <Button
        title={editingId ? t('wellbeing.updateRoutine') : t('wellbeing.addRoutine')}
        onPress={() => save.mutate()}
        disabled={!title.trim()}
      />
      {editingId ? (
        <Button
          title={t('wellbeing.cancelEdit')}
          variant="secondary"
          onPress={() => {
            setEditingId(null);
            setTitle('');
            setEnd('');
          }}
        />
      ) : null}

      {items.map((item) => (
        <Card key={String(item.id)} style={styles.card}>
          <Text style={styles.name}>{String(item.title)}</Text>
          <Text style={styles.meta}>
            {String(item.start_time)}
            {item.end_time ? `–${String(item.end_time)}` : ''} · {String(item.category)} ·{' '}
            {String(item.recurrence)} · {String(item.today_status ?? t('wellbeing.pending'))}
          </Text>
          <Text style={styles.meta}>
            {item.reminder_enabled ? t('wellbeing.remindersOn') : t('wellbeing.remindersOff')}
          </Text>
          <View style={styles.row}>
            <Button
              title={t('wellbeing.complete')}
              onPress={() => mark.mutate({ id: String(item.id), status: 'completed' })}
            />
            <Button
              title={t('wellbeing.skip')}
              variant="secondary"
              onPress={() => mark.mutate({ id: String(item.id), status: 'skipped' })}
            />
          </View>
          <View style={styles.row}>
            <Button
              title={t('wellbeing.editRoutine')}
              variant="secondary"
              onPress={() => {
                setEditingId(String(item.id));
                setTitle(String(item.title ?? ''));
                setStart(String(item.start_time ?? '08:00').slice(0, 5));
                setEnd(item.end_time ? String(item.end_time).slice(0, 5) : '');
                setCategory((CATEGORIES.find((c) => c === item.category) as (typeof CATEGORIES)[number]) || 'other');
                setRecurrence(
                  (RECURRENCE.find((r) => r === item.recurrence) as (typeof RECURRENCE)[number]) || 'daily',
                );
                setReminders(Boolean(item.reminder_enabled));
                setMinutesBefore(String(item.reminder_minutes_before ?? 15));
              }}
            />
            <Button
              title={t('wellbeing.deleteRoutine')}
              variant="secondary"
              onPress={() => remove.mutate(String(item.id))}
            />
          </View>
        </Card>
      ))}
      {message ? <Text style={styles.meta}>{message}</Text> : null}
      {save.error || mark.error || remove.error ? (
        <Text style={styles.error}>{hmoreErrorMessage(save.error || mark.error || remove.error)}</Text>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  disclaimer: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 12, marginBottom: theme.spacing.sm },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: 6 },
  label: { fontFamily: FONT_MEDIUM, color: theme.colors.text, marginBottom: 8, marginTop: 4 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: theme.spacing.sm },
  chip: { borderWidth: 1, borderColor: theme.colors.border, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 8 },
  chipOn: { backgroundColor: theme.colors.text, borderColor: theme.colors.text },
  chipText: { fontFamily: FONT_MEDIUM, color: theme.colors.text, fontSize: 13 },
  chipTextOn: { color: theme.colors.background },
  remindChip: { alignSelf: 'flex-start', marginBottom: theme.spacing.sm },
  card: { marginTop: theme.spacing.sm, gap: 8 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  row: { gap: 8 },
  error: { fontFamily: FONT_MEDIUM, color: theme.colors.danger, marginTop: 8 },
});
