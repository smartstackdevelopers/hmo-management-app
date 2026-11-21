import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { RefreshControl, StyleSheet, Text, View } from 'react-native';

import { FilterChips, SearchField } from '@/components/dashboard/mobileChrome';
import { StatusRow, statusTone } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
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

function verificationLabel(status: string | undefined, t: (key: string) => string): string {
  if (status === 'verified') return t('community.verified');
  if (status === 'outdated') return t('community.outdated');
  if (status === 'needs_review') return t('community.needsReview');
  return t('community.unverified');
}

function verificationTone(status: string | undefined) {
  if (status === 'verified') return 'green' as const;
  if (status === 'outdated' || status === 'needs_review') return 'amber' as const;
  return 'gray' as const;
}

export default function CommunityScreen() {
  const { t, fontScale, prefs } = useI18n();
  const router = useRouter();
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
    <Screen
      style={contrast ? styles.contrast : undefined}
      refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={query.refetch} tintColor={theme.colors.secondary} />}
    >
      <Text style={[styles.title, { fontSize: 28 * fontScale }, contrast && styles.contrastText]} accessibilityRole="header">
        {t('community.title')}
      </Text>
      <SearchField
        value={q}
        onChangeText={(value) => {
          setPage(1);
          setQ(value);
        }}
        placeholder={t('community.search')}
      />
      <FilterChips
        value={category}
        onChange={(id) => {
          setCategory(id);
          setPage(1);
        }}
        options={CATEGORIES.map((item) => ({ id: item.id, label: t(item.labelKey) }))}
      />
      {items.length === 0 ? (
        <Text style={[styles.empty, { fontSize: 16 * fontScale }]}>
          {q || category ? t('community.noResults') : t('community.empty')}
        </Text>
      ) : (
        items.map((item) => (
          <StatusRow
            key={item.id}
            name={item.name}
            title={item.name}
            subtitle={[
              t(CATEGORIES.find((entry) => entry.id === item.category)?.labelKey ?? 'community.localService'),
              item.address_line?.trim() || null,
            ].filter(Boolean).join(' · ')}
            chip={verificationLabel(item.verification_status, t)}
            tone={verificationTone(item.verification_status) || statusTone(item.verification_status)}
            onPress={() => router.push(`/(app)/community/${item.id}`)}
          />
        ))
      )}
      {totalPages > 1 ? (
        <View style={styles.pager}>
          <Button
            title={t('community.prevPage')}
            accessibilityLabel={t('community.prevPage')}
            variant="outline"
            onPress={() => setPage((current) => Math.max(1, current - 1))}
            disabled={page <= 1}
          />
          <Text style={styles.meta}>
            {page} / {totalPages}
          </Text>
          <Button
            title={t('community.nextPage')}
            accessibilityLabel={t('community.nextPage')}
            variant="outline"
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
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4 },
  lead: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: theme.spacing.md, marginTop: 4 },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 22 },
  pager: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8, marginTop: theme.spacing.md },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary },
});
