import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';

import { NearbyMap } from '@/components/help/NearbyMap';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { searchNearby } from '@/lib/hmore/services/helpNearMe';

const CATEGORIES = [
  { id: '', labelKey: 'helpNearMe.all' },
  { id: 'food_bank', labelKey: 'community.foodBank' },
  { id: 'kitchen', labelKey: 'community.kitchen' },
  { id: 'clothing_bank', labelKey: 'community.clothingBank' },
  { id: 'local_service', labelKey: 'community.localService' },
] as const;

const RADII = [1, 3, 5, 10, 15] as const;

function verificationLabel(status: string, t: (key: string) => string): string {
  if (status === 'verified') return t('community.verified');
  if (status === 'outdated') return t('community.outdated');
  if (status === 'needs_review') return t('community.needsReview');
  return t('community.unverified');
}

export default function HelpNearMeScreen() {
  const { t, fontScale } = useI18n();
  const router = useRouter();
  const [draft, setDraft] = useState('');
  const [postcode, setPostcode] = useState('');
  const [category, setCategory] = useState('');
  const [radiusKm, setRadiusKm] = useState(5);
  const [sort, setSort] = useState<'distance' | 'name'>('distance');
  const [view, setView] = useState<'list' | 'map'>('list');
  const [page, setPage] = useState(1);

  const query = useQuery({
    queryKey: ['hmore', 'help-near-me', postcode, category, radiusKm, sort, page],
    queryFn: () =>
      searchNearby({
        postcode,
        category: category || undefined,
        radius_km: radiusKm,
        sort,
        page,
        page_size: 20,
      }),
    enabled: Boolean(postcode),
  });

  const runSearch = () => {
    setPage(1);
    setPostcode(draft.trim());
  };

  const reset = () => {
    setDraft('');
    setPostcode('');
    setCategory('');
    setRadiusKm(5);
    setSort('distance');
    setView('list');
    setPage(1);
  };

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 24 * fontScale }]}>{t('helpNearMe.title')}</Text>
      <Text style={styles.lead}>{t('helpNearMe.lead')}</Text>
      <Input
        label={t('helpNearMe.postcode')}
        value={draft}
        onChangeText={setDraft}
        autoCapitalize="characters"
        accessibilityLabel={t('helpNearMe.postcode')}
        placeholder="e.g. SW1A 1AA"
      />
      <View style={styles.row}>
        <Button title={t('helpNearMe.search')} onPress={runSearch} accessibilityLabel={t('helpNearMe.search')} />
        <Button title={t('helpNearMe.reset')} variant="secondary" onPress={reset} accessibilityLabel={t('helpNearMe.reset')} />
      </View>

      <Text style={styles.filterLabel}>{t('helpNearMe.radius')}</Text>
      <View style={styles.filters}>
        {RADII.map((value) => (
          <Pressable
            key={value}
            accessibilityRole="button"
            accessibilityState={{ selected: radiusKm === value }}
            onPress={() => {
              setRadiusKm(value);
              setPage(1);
            }}
            style={[styles.chip, radiusKm === value && styles.chipOn]}
          >
            <Text style={[styles.chipText, radiusKm === value && styles.chipTextOn]}>{value} km</Text>
          </Pressable>
        ))}
      </View>

      <View style={styles.filters}>
        {CATEGORIES.map((item) => {
          const selected = category === item.id;
          return (
            <Pressable
              key={item.labelKey}
              accessibilityRole="button"
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

      <View style={styles.row}>
        <Button
          title={t('helpNearMe.sortDistance')}
          variant={sort === 'distance' ? 'primary' : 'secondary'}
          onPress={() => setSort('distance')}
        />
        <Button
          title={t('helpNearMe.sortName')}
          variant={sort === 'name' ? 'primary' : 'secondary'}
          onPress={() => setSort('name')}
        />
        <Button
          title={view === 'list' ? t('helpNearMe.mapView') : t('helpNearMe.listView')}
          variant="secondary"
          onPress={() => setView((current) => (current === 'list' ? 'map' : 'list'))}
        />
      </View>

      {!postcode ? (
        <Text style={styles.empty}>{t('helpNearMe.prompt')}</Text>
      ) : query.isLoading ? (
        <LoadingScreen message={t('helpNearMe.loading')} />
      ) : query.error ? (
        <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />
      ) : !query.data || query.data.items.length === 0 ? (
        <Text style={styles.empty}>{t('helpNearMe.empty')}</Text>
      ) : (
        <>
          <Text style={styles.meta}>
            {t('helpNearMe.resultsFor')} {query.data.postcode} · {query.data.total} · {query.data.radius_km} km
          </Text>
          {view === 'map' ? (
            <NearbyMap
              originLat={query.data.latitude}
              originLon={query.data.longitude}
              postcode={query.data.postcode}
              items={query.data.items}
              onSelect={(id) =>
                router.push({
                  pathname: '/(app)/help-near-me/[id]',
                  params: { id, postcode: query.data.postcode },
                })
              }
            />
          ) : (
            query.data.items.map((item) => (
              <Pressable
                key={item.id}
                accessibilityRole="button"
                accessibilityLabel={item.name}
                onPress={() =>
                  router.push({
                    pathname: '/(app)/help-near-me/[id]',
                    params: {
                      id: item.id,
                      postcode: query.data.postcode,
                      distance_km: String(item.distance_km),
                    },
                  })
                }
              >
                <Card style={styles.card}>
                  <Text style={styles.name}>{item.name}</Text>
                  <Text style={styles.meta}>
                    {item.distance_km} km ({item.distance_miles} mi) · {verificationLabel(item.verification_status, t)}
                  </Text>
                  {item.address_line ? <Text style={styles.body}>{item.address_line}</Text> : (
                    <Text style={styles.missing}>{t('community.notProvided')}</Text>
                  )}
                  <Text style={styles.meta}>
                    {t('community.hours')}: {item.opening_hours?.trim() ? item.opening_hours : t('community.notProvided')}
                  </Text>
                </Card>
              </Pressable>
            ))
          )}
          {query.data.total > query.data.page_size ? (
            <View style={styles.row}>
              <Button
                title={t('community.prevPage')}
                variant="secondary"
                disabled={page <= 1}
                onPress={() => setPage((current) => Math.max(1, current - 1))}
              />
              <Button
                title={t('community.nextPage')}
                variant="secondary"
                disabled={page * query.data.page_size >= query.data.total}
                onPress={() => setPage((current) => current + 1)}
              />
            </View>
          ) : null}
        </>
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  lead: {
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    marginBottom: theme.spacing.md,
    lineHeight: 20,
  },
  row: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginVertical: theme.spacing.sm },
  filterLabel: {
    fontFamily: FONT_SEMIBOLD,
    color: theme.colors.textMuted,
    marginTop: theme.spacing.sm,
    marginBottom: 6,
  },
  filters: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginBottom: theme.spacing.sm },
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
  missing: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.textMuted, marginTop: 6, fontStyle: 'italic' },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6 },
});
