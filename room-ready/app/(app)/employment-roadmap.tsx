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
import { createCareerGoal, getRoadmap } from '@/lib/hmore/services/employment';

export default function EmploymentRoadmapScreen() {
  const { t, fontScale } = useI18n();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['hmore', 'employment-roadmap'], queryFn: getRoadmap });
  const [goal, setGoal] = useState('');

  const create = useMutation({
    mutationFn: () =>
      createCareerGoal({
        title: goal.trim(),
        description: null,
        status: 'pending',
        suggested_activities: ['Update CV', 'Practise interview answers'],
      }),
    onSuccess: async () => {
      setGoal('');
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'employment-roadmap'] });
    },
  });

  if (query.isLoading) return <LoadingScreen message={t('employment.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const skills = (query.data?.current_skills as Array<Record<string, unknown>> | undefined) ?? [];
  const gaps = (query.data?.skill_gaps as string[] | undefined) ?? [];
  const learning = (query.data?.suggested_learning as string[] | undefined) ?? [];
  const goals = (query.data?.goals as Array<Record<string, unknown>> | undefined) ?? [];

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('employment.roadmap')}</Text>
      <Text style={styles.note}>{t('employment.roadmapNote')}</Text>
      <Card style={styles.card}>
        <Text style={styles.label}>{t('employment.skills')}</Text>
        <Text style={styles.body}>
          {skills.length ? skills.map((item) => String(item.name)).join(', ') : t('employment.noSkills')}
        </Text>
        <Text style={styles.label}>{t('employment.goals')}</Text>
        <Text style={styles.body}>{String(query.data?.employment_goals || t('community.notProvided'))}</Text>
      </Card>
      <Card style={styles.card}>
        <Text style={styles.label}>{t('employment.gaps')}</Text>
        {gaps.map((item) => (
          <Text key={item} style={styles.body}>
            • {item}
          </Text>
        ))}
        <Text style={styles.label}>{t('employment.learning')}</Text>
        {learning.map((item) => (
          <Text key={item} style={styles.body}>
            • {item}
          </Text>
        ))}
      </Card>
      <Input label={t('employment.newGoal')} value={goal} onChangeText={setGoal} />
      <Button title={t('employment.saveGoal')} onPress={() => create.mutate()} disabled={!goal.trim() || create.isPending} />
      {goals.map((item) => (
        <Card key={String(item.id)} style={styles.card}>
          <Text style={styles.name}>{String(item.title)}</Text>
          <Text style={styles.meta}>{String(item.status)}</Text>
        </Card>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text },
  note: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginVertical: 8, lineHeight: 20 },
  card: { marginBottom: 10 },
  label: { fontFamily: FONT_BOLD, color: theme.colors.textMuted, marginTop: 6 },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text, lineHeight: 20, marginTop: 4 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, marginTop: 4 },
});
