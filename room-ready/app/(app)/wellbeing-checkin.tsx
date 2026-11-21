import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Chip } from '@/components/ui/Chip';
import { Input } from '@/components/ui/Input';
import { Screen } from '@/components/ui/Screen';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { upsertCheckin } from '@/lib/hmore/services/wellbeing';

const MOODS = [
  { id: 'very_good', labelKey: 'wellbeing.moodVeryGood' },
  { id: 'good', labelKey: 'wellbeing.moodGood' },
  { id: 'okay', labelKey: 'wellbeing.moodOkay' },
  { id: 'low', labelKey: 'wellbeing.moodLow' },
  { id: 'very_low', labelKey: 'wellbeing.moodVeryLow' },
] as const;

export default function WellbeingCheckinScreen() {
  const { t, fontScale } = useI18n();
  const queryClient = useQueryClient();
  const [mood, setMood] = useState<string | null>(null);
  const [energy, setEnergy] = useState('');
  const [stress, setStress] = useState('');
  const [notes, setNotes] = useState('');
  const [message, setMessage] = useState<string | null>(null);

  const save = useMutation({
    mutationFn: (skipped: boolean) =>
      upsertCheckin({
        skipped,
        mood: skipped ? null : mood,
        energy_level: skipped || !energy ? null : Number(energy),
        stress_level: skipped || !stress ? null : Number(stress),
        notes: skipped || !notes.trim() ? null : notes.trim(),
      }),
    onSuccess: async () => {
      setMessage(t('wellbeing.saved'));
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'wellbeing-dashboard'] });
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'wellbeing-history'] });
    },
  });

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('wellbeing.checkin')}</Text>
      <Text style={styles.disclaimer}>{t('wellbeing.disclaimer')}</Text>
      <Text style={styles.label}>{t('wellbeing.moodOptional')}</Text>
      <View style={styles.moods}>
        {MOODS.map((item) => (
          <Chip
            key={item.id}
            label={t(item.labelKey)}
            selected={mood === item.id}
            onPress={() => setMood(item.id)}
          />
        ))}
      </View>
      <Input label={t('wellbeing.energyOptional')} value={energy} onChangeText={setEnergy} keyboardType="number-pad" />
      <Input label={t('wellbeing.stressOptional')} value={stress} onChangeText={setStress} keyboardType="number-pad" />
      <Input label={t('wellbeing.notesOptional')} value={notes} onChangeText={setNotes} />
      <Button title={t('wellbeing.saveCheckin')} onPress={() => save.mutate(false)} fullWidth />
      <Button title={t('wellbeing.skipCheckin')} variant="outline" onPress={() => save.mutate(true)} fullWidth />
      {message ? <Text style={styles.meta}>{message}</Text> : null}
      {save.error ? <Text style={styles.error}>{hmoreErrorMessage(save.error)}</Text> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.xs },
  disclaimer: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 12, marginBottom: theme.spacing.md },
  label: { fontFamily: FONT_MEDIUM, color: theme.colors.text, marginBottom: 8 },
  moods: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: theme.spacing.md },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 8 },
  error: { fontFamily: FONT_MEDIUM, color: theme.colors.danger, marginTop: 8 },
});
