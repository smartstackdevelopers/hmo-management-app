import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { StatusRow } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Chip } from '@/components/ui/Chip';
import { Input } from '@/components/ui/Input';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import {
  assistCvWording,
  createCv,
  deleteCv,
  duplicateCv,
  generateCvPdf,
  listCvs,
  updateCv,
} from '@/lib/hmore/services/employment';

const TEMPLATES = [
  'simple_professional',
  'modern_professional',
  'entry_level',
  'skills_based',
  'experienced_worker',
] as const;

export default function EmploymentCvsScreen() {
  const { t, fontScale } = useI18n();
  const router = useRouter();
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['hmore', 'employment-cvs'], queryFn: listCvs });
  const [title, setTitle] = useState('My CV');
  const [template, setTemplate] = useState<string>('simple_professional');
  const [profile, setProfile] = useState('');
  const [assistOut, setAssistOut] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const refresh = async () => {
    await queryClient.invalidateQueries({ queryKey: ['hmore', 'employment-cvs'] });
  };

  const create = useMutation({
    mutationFn: () =>
      createCv({
        title,
        template_id: template,
        seed_from_assessment: true,
        is_default: false,
        content: profile.trim() ? { personal_profile: profile.trim() } : undefined,
      }),
    onSuccess: async () => {
      setMessage(t('employment.saved'));
      await refresh();
    },
  });

  if (query.isLoading) return <LoadingScreen message={t('employment.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const items = query.data?.items ?? [];

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('employment.cvs')}</Text>
      <Input label={t('employment.cvTitle')} value={title} onChangeText={setTitle} />
      <Text style={styles.label}>{t('employment.template')}</Text>
      <View style={styles.row}>
        {TEMPLATES.map((item) => (
          <Chip
            key={item}
            label={item.replaceAll('_', ' ')}
            selected={template === item}
            onPress={() => setTemplate(item)}
          />
        ))}
      </View>
      <Input label={t('employment.profile')} value={profile} onChangeText={setProfile} />
      <Button
        title={t('employment.aiAssist')}
        variant="secondary"
        onPress={async () => {
          if (!profile.trim()) return;
          try {
            const result = await assistCvWording({ field: 'personal_profile', original_text: profile });
            setAssistOut(String(result.suggested_text ?? ''));
          } catch (error) {
            setAssistOut(hmoreErrorMessage(error));
          }
        }}
      />
      {assistOut ? (
        <Card style={styles.card}>
          <Text style={styles.label}>{t('employment.aiSuggestion')}</Text>
          <Text style={styles.body}>{assistOut}</Text>
          <Button title={t('employment.useSuggestion')} variant="outline" onPress={() => setProfile(assistOut)} />
        </Card>
      ) : null}
      <Button title={t('employment.createCv')} onPress={() => create.mutate()} disabled={create.isPending} fullWidth />
      {items.map((cv) => {
        const id = String(cv.id);
        const completion = (cv.completion as { percent?: number } | undefined)?.percent;
        return (
          <View key={id} style={styles.card}>
            <StatusRow
              name={String(cv.title)}
              title={String(cv.title)}
              subtitle={[String(cv.template_id).replaceAll('_', ' '), completion != null ? `${completion}%` : null, `v${String(cv.version)}`].filter(Boolean).join(' · ')}
              chip={cv.is_default ? t('employment.setDefault') : undefined}
              tone="blue"
              onPress={() => router.push(`/(app)/employment-cv/${id}`)}
            />
            <View style={styles.actions}>
              <Button
                title={t('employment.preview')}
                variant="outline"
                onPress={() => router.push(`/(app)/employment-cv/${id}`)}
              />
              <Button
                title={t('employment.pdf')}
                variant="outline"
                onPress={async () => {
                  await generateCvPdf(id);
                  setMessage(t('employment.pdfReady'));
                  await refresh();
                }}
              />
              <Button title={t('employment.duplicate')} variant="outline" onPress={async () => { await duplicateCv(id); await refresh(); }} />
              <Button title={t('employment.delete')} variant="outline" onPress={async () => { await deleteCv(id); await refresh(); }} />
            </View>
            <Button
              title={t('employment.setDefault')}
              variant="ghost"
              onPress={async () => {
                await updateCv(id, { is_default: true });
                await refresh();
              }}
            />
          </View>
        );
      })}
      {message ? <Text style={styles.ok}>{message}</Text> : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: 8 },
  label: { fontFamily: FONT_BOLD, color: theme.colors.textMuted, marginBottom: 6, marginTop: 8 },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 10 },
  actions: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: 4 },
  card: { marginBottom: 10 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, marginVertical: 6 },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 20, marginBottom: 8 },
  ok: { fontFamily: FONT_MEDIUM, color: theme.colors.secondary, marginTop: 8 },
});
