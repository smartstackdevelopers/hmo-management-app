import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getInterviewPrep, saveInterviewPrep } from '@/lib/hmore/services/employment';

export default function EmploymentInterviewScreen() {
  const { t, fontScale } = useI18n();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['hmore', 'employment-interview'], queryFn: getInterviewPrep });
  const [notes, setNotes] = useState('');
  const [questions, setQuestions] = useState('');

  const save = useMutation({
    mutationFn: () =>
      saveInterviewPrep({
        notes: notes.trim() || null,
        questions_to_ask: questions.trim() || null,
        checklist: null,
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'employment-interview'] });
    },
  });

  if (query.isLoading) return <LoadingScreen message={t('employment.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const common = (query.data?.common_questions as string[] | undefined) ?? [];

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('employment.interview')}</Text>
      <Text style={styles.note}>{t('employment.interviewNote')}</Text>
      <Card style={styles.card}>
        {common.map((item) => (
          <Text key={item} style={styles.body}>
            • {item}
          </Text>
        ))}
      </Card>
      <Input label={t('employment.interviewNotes')} value={notes} onChangeText={setNotes} />
      <Input label={t('employment.questionsToAsk')} value={questions} onChangeText={setQuestions} />
      <Button title={t('employment.save')} onPress={() => save.mutate()} disabled={save.isPending} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text },
  note: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginVertical: 8, lineHeight: 20 },
  card: { marginBottom: 12 },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text, lineHeight: 22, marginBottom: 4 },
});
