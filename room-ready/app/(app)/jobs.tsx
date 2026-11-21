import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { StyleSheet, Text } from 'react-native';

import { FilterChips, SearchField } from '@/components/dashboard/mobileChrome';
import { StatusRow } from '@/components/staff/ui';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
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
      <Text style={[styles.title, { fontSize: 28 * fontScale }, contrast && styles.contrastText]} accessibilityRole="header">{t('jobs.title')}</Text>
      <SearchField
        value={draft}
        onChangeText={(value) => {
          setDraft(value);
          setQ(value.trim());
        }}
        placeholder={t('jobs.search')}
      />
      <FilterChips
        value={kind}
        onChange={setKind}
        options={KINDS.map((item) => ({ id: item.id, label: t(item.labelKey) }))}
      />
      {items.length === 0 ? (
        <Text style={[styles.empty, { fontSize: 16 * fontScale }]}>{t('jobs.empty')}</Text>
      ) : (
        items.map((item) => (
          <StatusRow
            key={item.id}
            name={item.title}
            title={item.title}
            subtitle={[item.kind === 'training' ? t('jobs.training') : t('jobs.jobs'), item.source_name || null].filter(Boolean).join(' · ')}
            chip={item.kind === 'training' ? t('jobs.training') : t('jobs.jobs')}
            tone={item.kind === 'training' ? 'indigo' : 'blue'}
          />
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.md },
  linkRow: { flexDirection: 'row', gap: 8, marginBottom: theme.spacing.sm },
  linkHalf: { flex: 1 },
  filters: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginVertical: theme.spacing.md },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 22, marginTop: theme.spacing.md },
  card: { marginBottom: theme.spacing.sm },
  cardBody: { paddingHorizontal: theme.spacing.md, paddingBottom: theme.spacing.md },
  body: { fontFamily: FONT_MEDIUM, fontSize: 14, color: theme.colors.textSecondary, marginTop: 6, lineHeight: 20 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6 },
});
