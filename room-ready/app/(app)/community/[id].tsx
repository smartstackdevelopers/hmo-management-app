import { useQuery } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';
import { Linking, Platform, StyleSheet, Text, View } from 'react-native';

import { FactGrid } from '@/components/dashboard/mobileChrome';
import { Button } from '@/components/ui/Button';
import { Chip } from '@/components/ui/Chip';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getCommunityService } from '@/lib/hmore/services/community';

const CATEGORY_LABEL: Record<string, string> = {
  food_bank: 'community.foodBank',
  kitchen: 'community.kitchen',
  clothing_bank: 'community.clothingBank',
  local_service: 'community.localService',
};

const CLOTHING_LABEL: Record<string, string> = {
  provides_clothing: 'community.providesClothing',
  accepts_donations: 'community.acceptsDonations',
  both: 'community.clothingBoth',
};

export default function CommunityServiceDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { t, fontScale, prefs } = useI18n();
  const query = useQuery({
    queryKey: ['hmore', 'community-service', id],
    queryFn: () => getCommunityService(String(id)),
    enabled: Boolean(id),
  });

  if (query.isLoading) return <LoadingScreen message={t('community.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;
  if (!query.data) return <ErrorState message={t('community.missingDetail')} onRetry={query.refetch} />;

  const item = query.data;
  const contrast = prefs.highContrast;
  const categoryKey = CATEGORY_LABEL[item.category] ?? 'community.localService';
  const verifiedLabel =
    item.verification_status === 'verified'
      ? t('community.verified')
      : item.verification_status === 'outdated'
        ? t('community.outdated')
        : item.verification_status === 'needs_review'
          ? t('community.needsReview')
          : t('community.unverified');

  const facts = [
    item.opening_hours?.trim() ? { label: t('community.hours'), value: item.opening_hours.trim() } : null,
    item.opening_days?.trim() ? { label: t('community.openingDays'), value: item.opening_days.trim() } : null,
    item.contact?.trim() ? { label: t('community.contact'), value: item.contact.trim() } : null,
    item.referral_requirements?.trim() ? { label: t('community.referral'), value: item.referral_requirements.trim() } : null,
    item.eligibility?.trim() ? { label: t('community.eligibility'), value: item.eligibility.trim() } : null,
    item.address_line?.trim() ? { label: t('community.address'), value: item.address_line.trim() } : null,
    item.category === 'clothing_bank' && item.clothing_service_type
      ? { label: t('community.clothingType'), value: t(CLOTHING_LABEL[item.clothing_service_type] ?? 'community.notProvided') }
      : null,
  ].filter((entry): entry is { label: string; value: string } => !!entry);

  const openDirections = () => {
    const queryText = encodeURIComponent(item.address_line || item.name);
    const apple = `http://maps.apple.com/?q=${queryText}`;
    const google = `https://www.google.com/maps/search/?api=1&query=${queryText}`;
    const osm = `https://www.openstreetmap.org/search?query=${queryText}`;
    const url = Platform.OS === 'ios' ? apple : Platform.OS === 'android' ? google : osm;
    return Linking.openURL(url);
  };

  return (
    <Screen style={contrast ? styles.contrast : undefined}>
      <Text style={[styles.title, { fontSize: 28 * fontScale }, contrast && styles.contrastText]} accessibilityRole="header">
        {item.name}
      </Text>
      {item.address_line ? <Text style={[styles.meta, { fontSize: 14 * fontScale }]}>{item.address_line}</Text> : null}
      <View style={styles.chips}>
        <Chip
          label={verifiedLabel}
          tone={item.verification_status === 'verified' ? 'green' : item.verification_status === 'outdated' ? 'amber' : 'gray'}
        />
        <Chip label={t(categoryKey)} tone="blue" />
      </View>
      {facts.length ? <FactGrid items={facts} /> : null}
      {item.description?.trim() ? <Text style={styles.body}>{item.description}</Text> : null}
      {item.service_instructions?.trim() ? <Text style={styles.body}>{item.service_instructions}</Text> : null}
      {item.address_line?.trim() ? (
        <Button title={t('helpNearMe.directions')} onPress={openDirections} fullWidth accessibilityLabel={t('helpNearMe.directions')} />
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: 4 },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginTop: 4 },
  chips: { flexDirection: 'row', flexWrap: 'wrap', gap: 8, marginTop: 12, marginBottom: 4 },
  body: { fontFamily: FONT_MEDIUM, color: theme.colors.text, lineHeight: 22, marginBottom: theme.spacing.md },
});
