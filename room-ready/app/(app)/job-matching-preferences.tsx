import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getJobMatchPreferences, updateJobMatchPreferences } from '@/lib/hmore/services/jobMatching';

function joinList(value: unknown): string {
  return Array.isArray(value) ? value.map(String).join(', ') : '';
}

export default function JobMatchingPreferencesScreen() {
  const { t, fontScale } = useI18n();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['hmore', 'job-matching-preferences'], queryFn: getJobMatchPreferences });
  const [categories, setCategories] = useState('');
  const [locations, setLocations] = useState('');
  const [types, setTypes] = useState('');
  const [interests, setInterests] = useState('');
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!query.data) return;
    setCategories(joinList(query.data.preferred_categories));
    setLocations(joinList(query.data.preferred_locations));
    setTypes(joinList(query.data.preferred_employment_types));
    setInterests(joinList(query.data.career_interests));
  }, [query.data]);

  const save = useMutation({
    mutationFn: () =>
      updateJobMatchPreferences({
        preferred_categories: categories.split(',').map((s) => s.trim()).filter(Boolean),
        preferred_locations: locations.split(',').map((s) => s.trim()).filter(Boolean),
        preferred_employment_types: types.split(',').map((s) => s.trim()).filter(Boolean),
        career_interests: interests.split(',').map((s) => s.trim()).filter(Boolean),
      }),
    onSuccess: async () => {
      setMessage(t('employment.saved'));
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'job-matching-preferences'] });
    },
  });

  if (query.isLoading) return <LoadingScreen message={t('jobMatching.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('jobMatching.preferences')}</Text>
      <Text style={styles.meta}>{t('jobMatching.preferencesHelp')}</Text>
      <Input label={t('jobMatching.categories')} value={categories} onChangeText={setCategories} />
      <Input label={t('employment.location')} value={locations} onChangeText={setLocations} />
      <Input label={t('jobMatching.employmentTypes')} value={types} onChangeText={setTypes} />
      <Input label={t('employment.interests')} value={interests} onChangeText={setInterests} />
      <Button title={t('employment.save')} onPress={() => save.mutate()} />
      <Button
        title={t('jobMatching.resetPreferences')}
        variant="secondary"
        onPress={() =>
          updateJobMatchPreferences({ reset: true }).then(async () => {
            setMessage(t('employment.saved'));
            await queryClient.invalidateQueries({ queryKey: ['hmore', 'job-matching-preferences'] });
          })
        }
      />
      {message ? <Text style={styles.meta}>{message}</Text> : null}
      {save.error ? <Text style={styles.error}>{hmoreErrorMessage(save.error)}</Text> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: theme.spacing.sm },
  error: { fontFamily: FONT_MEDIUM, color: theme.colors.danger, marginTop: 8 },
});
