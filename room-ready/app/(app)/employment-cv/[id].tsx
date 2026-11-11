import { useQuery } from '@tanstack/react-query';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getCv } from '@/lib/hmore/services/employment';

export default function EmploymentCvPreviewScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
  const { t, fontScale } = useI18n();
  const query = useQuery({
    queryKey: ['hmore', 'employment-cv', id],
    queryFn: () => getCv(String(id)),
    enabled: Boolean(id),
  });

  if (query.isLoading) return <LoadingScreen message={t('employment.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;
  if (!query.data) return <ErrorState message={t('employment.missing')} onRetry={query.refetch} />;

  const content = (query.data.content as Record<string, unknown>) ?? {};
  const completion = (query.data.completion as { percent?: number; suggestions?: string[] }) ?? {};

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{String(query.data.title)}</Text>
      <Text style={styles.meta}>
        {String(query.data.template_id).replaceAll('_', ' ')} · {completion.percent ?? 0}%
      </Text>
      <Card style={styles.card}>
        <Text style={styles.label}>{t('employment.profile')}</Text>
        <Text style={styles.body}>{String(content.personal_profile || t('community.notProvided'))}</Text>
        <Text style={styles.label}>{t('employment.skills')}</Text>
        <Text style={styles.body}>
          {Array.isArray(content.skills) && content.skills.length
            ? content.skills
                .map((item) => (typeof item === 'object' && item && 'name' in item ? String((item as { name: string }).name) : String(item)))
                .join(', ')
            : t('community.notProvided')}
        </Text>
      </Card>
      {(completion.suggestions ?? []).map((item) => (
        <Text key={item} style={styles.meta}>
          • {item}
        </Text>
      ))}
      <Button title={t('community.backToDirectory')} variant="secondary" onPress={() => router.back()} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, marginVertical: 6 },
  card: { marginVertical: 12 },
  label: { fontFamily: FONT_BOLD, color: theme.colors.textMuted, marginTop: 8, marginBottom: 4 },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text, lineHeight: 22 },
});
