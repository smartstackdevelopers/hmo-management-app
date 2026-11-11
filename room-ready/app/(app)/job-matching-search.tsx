import { useRouter } from 'expo-router';
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
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
      <Text style={[styles.title, { fontSize: 22 * fontScale }]}>{t('jobMatching.search')}</Text>
      <Input label={t('jobMatching.keywords')} value={draft} onChangeText={setDraft} />
      <Input label={t('employment.location')} value={location} onChangeText={setLocation} />
      <Button
        title={t('jobMatching.searchAction')}
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
          <Pressable key={String(item.id)} onPress={() => router.push(`/(app)/job-matching-detail/${item.id}`)}>
            <Card style={styles.card}>
              <Text style={styles.name}>{String(item.title)}</Text>
              <Text style={styles.meta}>
                {String(item.employer_name)} · {String(item.source_name)}
                {item.score != null ? ` · ${t('jobMatching.score')} ${item.score}` : ''}
              </Text>
              {Array.isArray(item.reasons) && item.reasons[0] ? (
                <Text style={styles.body}>{String(item.reasons[0])}</Text>
              ) : null}
            </Card>
          </Pressable>
        ))
      )}
      <Text style={styles.disclaimer}>{query.data?.disclaimer}</Text>
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.sm },
  card: { marginTop: theme.spacing.sm },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 4 },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text, marginTop: 6 },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: theme.spacing.md },
  disclaimer: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: theme.spacing.lg, fontSize: 12 },
});
