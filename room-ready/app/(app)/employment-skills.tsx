import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
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
import { getAssessment, updateAssessment } from '@/lib/hmore/services/employment';

export default function EmploymentSkillsScreen() {
  const { t, fontScale } = useI18n();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['hmore', 'employment-assessment'], queryFn: getAssessment });
  const [skillName, setSkillName] = useState('');
  const [goals, setGoals] = useState('');
  const [interests, setInterests] = useState('');
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!query.data) return;
    setGoals(String(query.data.employment_goals ?? ''));
    const list = (query.data.career_interests as string[] | undefined) ?? [];
    setInterests(list.join(', '));
  }, [query.data]);

  const save = useMutation({
    mutationFn: async () => {
      const existingSkills = (query.data?.skills as Array<Record<string, unknown>> | undefined) ?? [];
      const skills = [...existingSkills];
      if (skillName.trim()) {
        skills.push({
          name: skillName.trim(),
          category: 'other',
          level: 'developing',
          is_custom: true,
          is_verified_certificate: false,
        });
      }
      return updateAssessment({
        skills,
        career_interests: interests
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        employment_goals: goals.trim() || null,
        mark_completed: false,
      });
    },
    onSuccess: async () => {
      setSkillName('');
      setMessage(t('employment.saved'));
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'employment-assessment'] });
    },
  });

  if (query.isLoading) return <LoadingScreen message={t('employment.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const skills = (query.data?.skills as Array<Record<string, unknown>> | undefined) ?? [];
  const summary = (query.data?.summary as Record<string, unknown> | undefined) ?? {};

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('employment.skills')}</Text>
      <Text style={styles.meta}>
        {t('employment.completion')}: {String(query.data?.completion_percent ?? 0)}% · {String(query.data?.status)}
      </Text>
      <Text style={styles.note}>{String(summary.note ?? '')}</Text>
      <Card style={styles.card}>
        {skills.length === 0 ? (
          <Text style={styles.empty}>{t('employment.noSkills')}</Text>
        ) : (
          skills.map((skill, index) => (
            <Text key={`${skill.name}-${index}`} style={styles.item}>
              {String(skill.name)} · {String(skill.category)} · {String(skill.level ?? 'n/a')}
            </Text>
          ))
        )}
      </Card>
      <Input label={t('employment.addSkill')} value={skillName} onChangeText={setSkillName} />
      <Input label={t('employment.interests')} value={interests} onChangeText={setInterests} />
      <Input label={t('employment.goals')} value={goals} onChangeText={setGoals} />
      <Button title={t('employment.save')} onPress={() => save.mutate()} disabled={save.isPending} />
      {message ? <Text style={styles.ok}>{message}</Text> : null}
      {save.error ? <Text style={styles.err}>{hmoreErrorMessage(save.error)}</Text> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: 6 },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, marginBottom: 8 },
  note: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: 12, lineHeight: 20 },
  card: { marginBottom: 12 },
  item: { fontFamily: FONT_MEDIUM, color: theme.colors.text, marginBottom: 6 },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
  ok: { fontFamily: FONT_MEDIUM, color: theme.colors.secondary, marginTop: 8 },
  err: { fontFamily: FONT_MEDIUM, color: '#B42318', marginTop: 8 },
});
