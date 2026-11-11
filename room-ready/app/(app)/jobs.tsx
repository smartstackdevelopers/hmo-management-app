import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listOpportunities } from '@/lib/hmore/services/jobs';

const KINDS = [
  { id: '', labelKey: 'jobs.all' },
  { id: 'job', labelKey: 'jobs.jobs' },
  { id: 'training', labelKey: 'jobs.training' },
] as const;

export default function JobsScreen() {
  const { t, fontScale, prefs } = useI18n();
  const router = useRouter();
  const [draft, setDraft] = useState('');
  const [q, setQ] = useState('');
  const [kind, setKind] = useState('');
  const query = useQuery({
    queryKey: ['hmore', 'opportunities', q, kind],
    queryFn: () => listOpportunities({ q: q || undefined, kind: kind || undefined }),
  });

  if (query.isLoading) return <LoadingScreen message={t('jobs.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const items = query.data ?? [];
  const contrast = prefs.highContrast;

  return (
    <Screen style={contrast ? styles.contrast : undefined}>
      <Text style={[styles.title, { fontSize: 24 * fontScale }, contrast && styles.contrastText]}>{t('jobs.title')}</Text>
      <View style={styles.linkRow}>
        <Button
          title={t('jobMatching.title')}
          variant="secondary"
          style={styles.linkHalf}
          onPress={() => router.push('/(app)/job-matching')}
        />
        <Button
          title={t('communityHub.title')}
          variant="secondary"
          style={styles.linkHalf}
          onPress={() => router.push('/(app)/community-hub')}
        />
      </View>
      <Input label={t('jobs.search')} value={draft} onChangeText={setDraft} accessibilityLabel={t('jobs.search')} />
      <Button title={t('jobs.searchAction')} accessibilityLabel={t('jobs.searchAction')} onPress={() => setQ(draft.trim())} />
      <View style={styles.filters}>
        {KINDS.map((item) => {
          const selected = kind === item.id;
          return (
            <Pressable
              key={item.id || 'all'}
              accessibilityRole="button"
              accessibilityLabel={t(item.labelKey)}
              accessibilityState={{ selected }}
              onPress={() => setKind(item.id)}
              style={[styles.chip, selected && styles.chipOn]}
            >
              <Text style={[styles.chipText, selected && styles.chipTextOn]}>{t(item.labelKey)}</Text>
            </Pressable>
          );
        })}
      </View>
      {items.length === 0 ? (
        <Text style={[styles.empty, { fontSize: 16 * fontScale }]}>{t('jobs.empty')}</Text>
      ) : (
        items.map((item) => (
          <Card key={item.id} style={styles.card}>
            <Text style={styles.name}>{item.title}</Text>
            <Text style={styles.meta}>{item.kind === 'training' ? t('jobs.training') : t('jobs.jobs')}</Text>
            {item.description ? <Text style={styles.body}>{item.description}</Text> : null}
            {item.eligibility ? (
              <Text style={styles.meta}>
                {t('jobs.eligibility')}: {item.eligibility}
              </Text>
            ) : null}
            {item.source_name ? (
              <Text style={styles.meta}>
                {t('jobs.source')}: {item.source_name}
              </Text>
            ) : null}
          </Card>
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.md },
  linkRow: { flexDirection: 'row', gap: 8, marginBottom: theme.spacing.sm },
  linkHalf: { flex: 1 },
  filters: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginVertical: theme.spacing.md },
  chip: {
    borderWidth: 1,
    borderColor: theme.colors.border,
    borderRadius: theme.radius.full,
    paddingHorizontal: 12,
    paddingVertical: 8,
    backgroundColor: theme.colors.surface,
  },
  chipOn: { backgroundColor: theme.colors.secondary, borderColor: theme.colors.secondary },
  chipText: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, fontSize: 13 },
  chipTextOn: { color: theme.colors.textInverse },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 22, marginTop: theme.spacing.md },
  card: { marginBottom: theme.spacing.sm },
  name: { fontFamily: FONT_BOLD, fontSize: 16, color: theme.colors.text },
  body: { fontFamily: FONT_MEDIUM, fontSize: 14, color: theme.colors.textSecondary, marginTop: 6, lineHeight: 20 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6 },
});
