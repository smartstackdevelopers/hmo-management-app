import { useRouter } from 'expo-router';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { StyleSheet, Text } from 'react-native';

import { FilterChips, SearchField } from '@/components/dashboard/mobileChrome';
import { StatusRow } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { searchMatchedJobs } from '@/lib/hmore/services/jobMatching';

export default function JobMatchingSearchScreen() {
  const { t, fontScale } = useI18n();
  const router = useRouter();
  const [draft, setDraft] = useState('');
  const [location, setLocation] = useState('');
  const [q, setQ] = useState('');
  const [loc, setLoc] = useState('');
  const query = useQuery({
    queryKey: ['hmore', 'job-matching-search', q, loc],
    queryFn: () =>
      searchMatchedJobs({
        q: q || undefined,
        location: loc || undefined,
        refresh_live: true,
        sort: 'relevance',
      }),
  });

  if (query.isLoading) return <LoadingScreen message={t('jobMatching.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const items = query.data?.items ?? [];

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 28 * fontScale }]} accessibilityRole="header">{t('jobMatching.search')}</Text>
      <SearchField value={draft} onChangeText={setDraft} placeholder={t('jobMatching.keywords')} />
      <FilterChips
        value="search"
        onChange={(id) => {
          if (id === 'recommended') router.push('/(app)/job-matching-recommended');
          if (id === 'saved') router.push('/(app)/job-matching-saved');
        }}
        options={[
          { id: 'search', label: t('jobMatching.search') },
          { id: 'recommended', label: t('jobMatching.recommended') },
          { id: 'saved', label: t('jobMatching.saved') },
        ]}
      />
      <Input label={t('employment.location')} value={location} onChangeText={setLocation} />
      <Button
        title={t('jobMatching.searchAction')}
        fullWidth
        onPress={() => {
          setQ(draft.trim());
          setLoc(location.trim());
        }}
      />
      {query.data?.sources_unavailable?.length ? (
        <Text style={styles.meta}>
          {t('jobMatching.sourcesUnavailable')}:{' '}
          {query.data.sources_unavailable.map((s) => String(s.source)).join(', ')}
        </Text>
      ) : null}
      {items.length === 0 ? (
        <Text style={styles.empty}>{t('jobMatching.empty')}</Text>
      ) : (
        items.map((item) => (
          <StatusRow
            key={String(item.id)}
            name={String(item.title)}
            title={String(item.title)}
            subtitle={[String(item.employer_name || ''), String(item.source_name || '')].filter((part) => part && part !== 'undefined').join(' · ')}
            chip={item.score != null ? String(item.score) : undefined}
            tone="green"
            onPress={() => router.push(`/(app)/job-matching-detail/${item.id}`)}
          />
        ))
      )}
      <Text style={styles.disclaimer}>{query.data?.disclaimer}</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4, marginBottom: theme.spacing.sm },
  card: { marginTop: theme.spacing.sm },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 4 },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text, marginTop: 6, marginHorizontal: theme.spacing.md, marginBottom: theme.spacing.md },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: theme.spacing.md },
  disclaimer: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: theme.spacing.lg, fontSize: 12 },
});
