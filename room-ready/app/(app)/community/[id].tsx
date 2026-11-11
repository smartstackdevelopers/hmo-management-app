import { useQuery } from '@tanstack/react-query';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
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

function Field({
  label,
  value,
  missingLabel,
  fontScale,
}: {
  label: string;
  value: string | null | undefined;
  missingLabel: string;
  fontScale: number;
}) {
  const display = value?.trim() ? value : missingLabel;
  return (
    <View style={styles.field}>
      <Text style={[styles.label, { fontSize: 12 * fontScale }]}>{label}</Text>
      <Text style={[styles.value, { fontSize: 15 * fontScale }, !value?.trim() && styles.missing]}>
        {display}
      </Text>
    </View>
  );
}

export default function CommunityServiceDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const router = useRouter();
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

  return (
    <Screen style={contrast ? styles.contrast : undefined}>
      <Text style={[styles.title, { fontSize: 24 * fontScale }, contrast && styles.contrastText]}>
        {item.name}
      </Text>
      <Text style={[styles.meta, { fontSize: 13 * fontScale }]}>{t(categoryKey)}</Text>
      <Card style={styles.card}>
        <Field
          label={t('community.description')}
          value={item.description}
          missingLabel={t('community.notProvided')}
          fontScale={fontScale}
        />
        <Field
          label={t('community.address')}
          value={item.address_line}
          missingLabel={t('community.notProvided')}
          fontScale={fontScale}
        />
        <Field
          label={t('community.openingDays')}
          value={item.opening_days}
          missingLabel={t('community.notProvided')}
          fontScale={fontScale}
        />
        <Field
          label={t('community.hours')}
          value={item.opening_hours}
          missingLabel={t('community.notProvided')}
          fontScale={fontScale}
        />
        <Field
          label={t('community.eligibility')}
          value={item.eligibility}
          missingLabel={t('community.notProvided')}
          fontScale={fontScale}
        />
        <Field
          label={t('community.referral')}
          value={item.referral_requirements}
          missingLabel={t('community.notProvided')}
          fontScale={fontScale}
        />
        <Field
          label={t('community.contact')}
          value={item.contact}
          missingLabel={t('community.notProvided')}
          fontScale={fontScale}
        />
        <Field
          label={t('community.instructions')}
          value={item.service_instructions}
          missingLabel={t('community.notProvided')}
          fontScale={fontScale}
        />
        {item.category === 'clothing_bank' ? (
          <Field
            label={t('community.clothingType')}
            value={
              item.clothing_service_type
                ? t(CLOTHING_LABEL[item.clothing_service_type] ?? 'community.notProvided')
                : null
            }
            missingLabel={t('community.notProvided')}
            fontScale={fontScale}
          />
        ) : null}
        <Field
          label={t('community.verification')}
          value={verifiedLabel}
          missingLabel={t('community.unverified')}
          fontScale={fontScale}
        />
        <Field
          label={t('community.lastVerified')}
          value={item.verified_at ? new Date(item.verified_at).toLocaleDateString() : null}
          missingLabel={t('community.notVerifiedYet')}
          fontScale={fontScale}
        />
        <Field
          label={t('community.updated')}
          value={item.updated_at ? new Date(item.updated_at).toLocaleDateString() : null}
          missingLabel={t('community.notProvided')}
          fontScale={fontScale}
        />
      </Card>
      <Button
        title={t('community.backToDirectory')}
        accessibilityLabel={t('community.backToDirectory')}
        onPress={() => router.back()}
      />
    </Screen>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, marginBottom: theme.spacing.md },
  card: { marginBottom: theme.spacing.md },
  field: { marginBottom: theme.spacing.md },
  label: { fontFamily: FONT_BOLD, color: theme.colors.textMuted, marginBottom: 4 },
  value: { fontFamily: FONT_MEDIUM, color: theme.colors.text, lineHeight: 22 },
  missing: { color: theme.colors.textSecondary, fontStyle: 'italic' },
});
