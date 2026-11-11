import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listCommunityServicesPage } from '@/lib/hmore/services/community';

const CATEGORIES = [
  { id: '', labelKey: 'community.all' },
  { id: 'food_bank', labelKey: 'community.foodBank' },
  { id: 'kitchen', labelKey: 'community.kitchen' },
  { id: 'clothing_bank', labelKey: 'community.clothingBank' },
  { id: 'local_service', labelKey: 'community.localService' },
] as const;

function verificationLabel(
  status: string | undefined,
  t: (key: string) => string,
): string {
  if (status === 'verified') return t('community.verified');
  if (status === 'outdated') return t('community.outdated');
  if (status === 'needs_review') return t('community.needsReview');
  return t('community.unverified');
}

export default function CommunityScreen() {
  const { t, fontScale, prefs } = useI18n();
  const router = useRouter();
  const [draft, setDraft] = useState('');
  const [q, setQ] = useState('');
  const [category, setCategory] = useState('');
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ['hmore', 'community-services', q, category, page],
    queryFn: () =>
      listCommunityServicesPage({
        q: q || undefined,
        category: category || undefined,
        page,
        page_size: 20,
      }),
  });

  if (query.isLoading) return <LoadingScreen message={t('community.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;

  const pageData = query.data;
  const items = pageData?.items ?? [];
  const total = pageData?.total ?? 0;
  const pageSize = pageData?.page_size ?? 20;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const contrast = prefs.highContrast;

  return (
    <Screen style={contrast ? styles.contrast : undefined}>
      <Text style={[styles.title, { fontSize: 24 * fontScale }, contrast && styles.contrastText]}>
        {t('community.title')}
      </Text>
      <View style={styles.linkRow}>
        <Button
          title={t('nav.helpNearMe')}
          accessibilityLabel={t('nav.helpNearMe')}
          variant="secondary"
          onPress={() => router.push('/(app)/help-near-me')}
          style={styles.linkHalf}
        />
        <Button
          title={t('communityHub.title')}
          accessibilityLabel={t('communityHub.title')}
          variant="secondary"
          onPress={() => router.push('/(app)/community-hub')}
          style={styles.linkHalf}
        />
      </View>
      <Input
        label={t('community.search')}
        value={draft}
        onChangeText={setDraft}
        accessibilityLabel={t('community.search')}
      />
      <View style={styles.searchRow}>
        <Button
          title={t('community.searchAction')}
          accessibilityLabel={t('community.searchAction')}
          onPress={() => {
            setPage(1);
            setQ(draft.trim());
          }}
        />
        <Button
          title={t('community.resetSearch')}
          accessibilityLabel={t('community.resetSearch')}
          variant="secondary"
          onPress={() => {
            setDraft('');
            setQ('');
            setCategory('');
            setPage(1);
          }}
        />
      </View>
      <View style={styles.filters}>
        {CATEGORIES.map((item) => {
          const selected = category === item.id;
          return (
            <Pressable
              key={item.labelKey}
              accessibilityRole="button"
              accessibilityLabel={t(item.labelKey)}
              accessibilityState={{ selected }}
              onPress={() => {
                setCategory(item.id);
                setPage(1);
              }}
              style={[styles.chip, selected && styles.chipOn]}
            >
              <Text style={[styles.chipText, selected && styles.chipTextOn]}>{t(item.labelKey)}</Text>
            </Pressable>
          );
        })}
      </View>
      {items.length === 0 ? (
        <Text style={[styles.empty, { fontSize: 16 * fontScale }]}>
          {q || category ? t('community.noResults') : t('community.empty')}
        </Text>
      ) : (
        items.map((item) => (
          <Pressable
            key={item.id}
            accessibilityRole="button"
            accessibilityLabel={item.name}
            onPress={() => router.push(`/(app)/community/${item.id}`)}
          >
            <Card style={styles.card}>
              <Text style={styles.name}>{item.name}</Text>
              <Text style={styles.meta}>
                {t(CATEGORIES.find((entry) => entry.id === item.category)?.labelKey ?? 'community.localService')}
                {' · '}
                {verificationLabel(item.verification_status, t)}
              </Text>
              {item.description ? <Text style={styles.body}>{item.description}</Text> : (
                <Text style={styles.missing}>{t('community.notProvided')}</Text>
              )}
              {item.address_line ? <Text style={styles.body}>{item.address_line}</Text> : null}
              <Text style={styles.meta}>
                {t('community.hours')}: {item.opening_hours?.trim() ? item.opening_hours : t('community.notProvided')}
              </Text>
              <Text style={styles.meta}>
                {t('community.eligibility')}:{' '}
                {item.eligibility?.trim() ? item.eligibility : t('community.notProvided')}
              </Text>
              {item.verified_at ? (
                <Text style={styles.meta}>
                  {t('community.lastVerified')}: {new Date(item.verified_at).toLocaleDateString()}
                </Text>
              ) : null}
            </Card>
          </Pressable>
        ))
      )}
      {totalPages > 1 ? (
        <View style={styles.pager}>
          <Button
            title={t('community.prevPage')}
            accessibilityLabel={t('community.prevPage')}
            variant="secondary"
            onPress={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page <= 1}
          />
          <Text style={styles.meta}>
            {page} / {totalPages}
          </Text>
          <Button
            title={t('community.nextPage')}
            accessibilityLabel={t('community.nextPage')}
            variant="secondary"
            onPress={() => setPage((current) => Math.min(totalPages, current + 1))}
            disabled={page >= totalPages}
          />
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.md },
  linkRow: { flexDirection: 'row', gap: 8, marginBottom: theme.spacing.sm },
  linkHalf: { flex: 1 },
  searchRow: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: theme.spacing.sm },
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
  missing: {
    fontFamily: FONT_MEDIUM,
    fontSize: 13,
    color: theme.colors.textMuted,
    marginTop: 6,
    fontStyle: 'italic',
  },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6 },
  pager: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
    marginTop: theme.spacing.md,
    marginBottom: theme.spacing.lg,
  },
});
