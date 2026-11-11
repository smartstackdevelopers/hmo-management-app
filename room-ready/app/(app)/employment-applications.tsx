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
import {
  createApplication,
  getApplicationDashboard,
  listApplications,
  updateApplication,
} from '@/lib/hmore/services/employment';

export default function EmploymentApplicationsScreen() {
  const { t, fontScale } = useI18n();
  const queryClient = useQueryClient();
  const dash = useQuery({ queryKey: ['hmore', 'employment-dash'], queryFn: getApplicationDashboard });
  const list = useQuery({ queryKey: ['hmore', 'employment-apps'], queryFn: () => listApplications() });
  const [employer, setEmployer] = useState('');
  const [jobTitle, setJobTitle] = useState('');
  const [location, setLocation] = useState('');

  const create = useMutation({
    mutationFn: () =>
      createApplication({
        employer_name: employer.trim(),
        job_title: jobTitle.trim(),
        job_location: location.trim() || null,
        status: 'preparing',
        application_date: new Date().toISOString().slice(0, 10),
      }),
    onSuccess: async () => {
      setEmployer('');
      setJobTitle('');
      setLocation('');
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'employment-dash'] });
      await queryClient.invalidateQueries({ queryKey: ['hmore', 'employment-apps'] });
    },
  });

  if (dash.isLoading || list.isLoading) return <LoadingScreen message={t('employment.loading')} />;
  if (dash.error || list.error) {
    return <ErrorState message={hmoreErrorMessage(dash.error || list.error)} onRetry={() => { dash.refetch(); list.refetch(); }} />;
  }

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('employment.applications')}</Text>
      <Card style={styles.card}>
        <Text style={styles.meta}>
          {t('employment.total')}: {String(dash.data?.total ?? 0)} · {t('employment.preparing')}:{' '}
          {String(dash.data?.preparing ?? 0)} · {t('employment.submitted')}: {String(dash.data?.submitted ?? 0)} ·{' '}
          {t('employment.interviews')}: {String(dash.data?.interviews_scheduled ?? 0)} · {t('employment.offers')}:{' '}
          {String(dash.data?.offers ?? 0)}
        </Text>
      </Card>
      <Input label={t('employment.employer')} value={employer} onChangeText={setEmployer} />
      <Input label={t('employment.jobTitle')} value={jobTitle} onChangeText={setJobTitle} />
      <Input label={t('employment.location')} value={location} onChangeText={setLocation} />
      <Button
        title={t('employment.addApplication')}
        onPress={() => create.mutate()}
        disabled={create.isPending || !employer.trim() || !jobTitle.trim()}
      />
      {(list.data?.items ?? []).map((item) => (
        <Card key={String(item.id)} style={styles.card}>
          <Text style={styles.name}>
            {String(item.job_title)} · {String(item.employer_name)}
          </Text>
          <Text style={styles.meta}>
            {String(item.status).replaceAll('_', ' ')} · {String(item.job_location || t('community.notProvided'))}
          </Text>
          <View style={styles.row}>
            <Button
              title={t('employment.markApplied')}
              variant="secondary"
              onPress={async () => {
                await updateApplication(String(item.id), { status: 'applied' });
                await queryClient.invalidateQueries({ queryKey: ['hmore', 'employment-apps'] });
                await queryClient.invalidateQueries({ queryKey: ['hmore', 'employment-dash'] });
              }}
            />
            <Button
              title={t('employment.markInterview')}
              variant="secondary"
              onPress={async () => {
                await updateApplication(String(item.id), {
                  status: 'interview_scheduled',
                  interview_at: new Date(Date.now() + 3 * 86400000).toISOString(),
                });
                await queryClient.invalidateQueries({ queryKey: ['hmore', 'employment-apps'] });
                await queryClient.invalidateQueries({ queryKey: ['hmore', 'employment-dash'] });
              }}
            />
          </View>
        </Card>
      ))}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: 8 },
  card: { marginBottom: 10 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, marginTop: 6, lineHeight: 20 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 8 },
});
