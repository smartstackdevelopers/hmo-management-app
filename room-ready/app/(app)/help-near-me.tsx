import { useQuery } from '@tanstack/react-query';
import { useRouter } from 'expo-router';
import { useState } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { NearbyMap } from '@/components/help/NearbyMap';
import { FilterChips, SearchField } from '@/components/dashboard/mobileChrome';
import { StatusRow } from '@/components/staff/ui';
import { Screen } from '@/components/ui/Screen';
import { ErrorState } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
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
  const [page, setPage] = useState(1);

  const query = useQuery({
    queryKey: ['hmore', 'help-near-me', postcode, category, radiusKm, page],
    queryFn: () =>
      searchNearby({
        postcode,
        category: category || undefined,
        radius_km: radiusKm,
        sort: 'distance',
        page,
        page_size: 20,
      }),
    enabled: Boolean(postcode),
  });

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 28 * fontScale }]} accessibilityRole="header">{t('helpNearMe.title')}</Text>
      <Text style={styles.lead}>{t('helpNearMe.lead')}</Text>
      <SearchField
        value={draft}
        onChangeText={(value) => {
          setDraft(value);
          const next = value.trim();
          if (next.length >= 5) {
            setPage(1);
            setPostcode(next);
          } else if (!next) {
            setPostcode('');
          }
        }}
        placeholder={t('helpNearMe.postcode')}
      />
      <FilterChips
        value={String(radiusKm)}
        onChange={(id) => {
          setRadiusKm(Number(id));
          setPage(1);
        }}
        options={RADII.map((value) => ({ id: String(value), label: `${value} km` }))}
      />
      <FilterChips
        value={category}
        onChange={(id) => {
          setCategory(id);
          setPage(1);
        }}
        options={CATEGORIES.map((item) => ({ id: item.id, label: t(item.labelKey) }))}
      />
      {!postcode ? <Text style={styles.empty}>{t('helpNearMe.prompt')}</Text> : null}
      {postcode && query.isLoading ? <Text style={styles.empty}>{t('helpNearMe.loading')}</Text> : null}
      {postcode && query.error ? <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} /> : null}
      {postcode && query.data && query.data.items.length === 0 ? <Text style={styles.empty}>{t('helpNearMe.empty')}</Text> : null}
      {postcode && query.data && query.data.items.length > 0 ? (
        <View>
          <Text style={styles.meta}>
            {query.data.total} · {query.data.radius_km} km
          </Text>
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
          {query.data.items.map((item) => (
            <StatusRow
              key={item.id}
              name={item.name}
              title={item.name}
              subtitle={[
                item.distance_km != null ? `${item.distance_km} km` : null,
                item.opening_hours?.trim() || null,
              ].filter(Boolean).join(' · ')}
              chip={verificationLabel(item.verification_status, t)}
              tone={item.verification_status === 'verified' ? 'green' : item.verification_status === 'outdated' ? 'amber' : 'gray'}
              onPress={() =>
                router.push({
                  pathname: '/(app)/help-near-me/[id]',
                  params: {
                    id: item.id,
                    postcode: query.data.postcode,
                    distance_km: item.distance_km != null ? String(item.distance_km) : '',
                  },
                })
              }
            />
          ))}
        </View>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.4 },
  lead: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 20, marginTop: 4, marginBottom: theme.spacing.md },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, lineHeight: 22 },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: 8 },
});
