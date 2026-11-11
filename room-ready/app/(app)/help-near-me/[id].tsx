import { useMutation, useQuery } from '@tanstack/react-query';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { useState } from 'react';
import { Linking, Platform, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM } from '@/constants/fonts';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getCommunityService } from '@/lib/hmore/services/community';
import { submitOutdatedReport } from '@/lib/hmore/services/helpNearMe';

const REPORT_REASONS = [
  { id: 'service_closed', labelKey: 'helpNearMe.reasonClosed' },
  { id: 'address_incorrect', labelKey: 'helpNearMe.reasonAddress' },
  { id: 'opening_hours_incorrect', labelKey: 'helpNearMe.reasonHours' },
  { id: 'contact_incorrect', labelKey: 'helpNearMe.reasonContact' },
  { id: 'eligibility_incorrect', labelKey: 'helpNearMe.reasonEligibility' },
  { id: 'information_outdated', labelKey: 'helpNearMe.reasonOutdated' },
  { id: 'cannot_locate', labelKey: 'helpNearMe.reasonLocate' },
  { id: 'other', labelKey: 'helpNearMe.reasonOther' },
] as const;

function Field({
  label,
  value,
  missing,
}: {
  label: string;
  value: string | null | undefined;
  missing: string;
}) {
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <Text style={[styles.value, !value?.trim() && styles.missing]}>{value?.trim() ? value : missing}</Text>
    </View>
  );
}

export default function HelpNearMeDetailScreen() {
  const { id, distance_km: distanceKm } = useLocalSearchParams<{
    id: string;
    postcode?: string;
    distance_km?: string;
  }>();
  const router = useRouter();
  const { t, fontScale } = useI18n();
  const [reason, setReason] = useState<string>('information_outdated');
  const [details, setDetails] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const query = useQuery({
    queryKey: ['hmore', 'community-service', id],
    queryFn: () => getCommunityService(String(id)),
    enabled: Boolean(id),
  });

  const reportMutation = useMutation({
    mutationFn: () =>
      submitOutdatedReport({
        service_id: String(id),
        reason,
        details: details.trim() || null,
      }),
    onSuccess: () => setSubmitted(true),
  });

  if (query.isLoading) return <LoadingScreen message={t('helpNearMe.loading')} />;
  if (query.error) return <ErrorState message={hmoreErrorMessage(query.error)} onRetry={query.refetch} />;
  if (!query.data) return <ErrorState message={t('community.missingDetail')} onRetry={query.refetch} />;

  const item = query.data;

  const openDirections = async () => {
    const queryText = encodeURIComponent(item.address_line || item.name);
    const apple = `http://maps.apple.com/?q=${queryText}`;
    const google = `https://www.google.com/maps/search/?api=1&query=${queryText}`;
    const osm = `https://www.openstreetmap.org/search?query=${queryText}`;
    const url = Platform.OS === 'ios' ? apple : Platform.OS === 'android' ? google : osm;
    await Linking.openURL(url);
  };

  return (
    <Screen>
      <Text style={[styles.title, { fontSize: 24 * fontScale }]}>{item.name}</Text>
      {distanceKm ? (
        <Text style={styles.meta}>
          {t('helpNearMe.distance')}: {distanceKm} km
        </Text>
      ) : null}
      <Card style={styles.card}>
        <Field label={t('community.description')} value={item.description} missing={t('community.notProvided')} />
        <Field label={t('community.address')} value={item.address_line} missing={t('community.notProvided')} />
        <Field label={t('community.openingDays')} value={item.opening_days} missing={t('community.notProvided')} />
        <Field label={t('community.hours')} value={item.opening_hours} missing={t('community.notProvided')} />
        <Field label={t('community.eligibility')} value={item.eligibility} missing={t('community.notProvided')} />
        <Field label={t('community.referral')} value={item.referral_requirements} missing={t('community.notProvided')} />
        <Field label={t('community.contact')} value={item.contact} missing={t('community.notProvided')} />
        <Field label={t('community.instructions')} value={item.service_instructions} missing={t('community.notProvided')} />
        <Field
          label={t('community.verification')}
          value={
            item.verification_status === 'verified'
              ? t('community.verified')
              : item.verification_status === 'outdated'
                ? t('community.outdated')
                : item.verification_status === 'needs_review'
                  ? t('community.needsReview')
                  : t('community.unverified')
          }
          missing={t('community.unverified')}
        />
        <Field
          label={t('community.lastVerified')}
          value={item.verified_at ? new Date(item.verified_at).toLocaleDateString() : null}
          missing={t('community.notVerifiedYet')}
        />
      </Card>

      <Button title={t('helpNearMe.directions')} onPress={openDirections} accessibilityLabel={t('helpNearMe.directions')} />
      <Button
        title={t('community.backToDirectory')}
        variant="secondary"
        onPress={() => router.back()}
        accessibilityLabel={t('community.backToDirectory')}
      />

      <Text style={[styles.section, { fontSize: 18 * fontScale }]}>{t('helpNearMe.reportTitle')}</Text>
      <Text style={styles.lead}>{t('helpNearMe.reportLead')}</Text>
      <View style={styles.reasons}>
        {REPORT_REASONS.map((entry) => (
          <Button
            key={entry.id}
            title={t(entry.labelKey)}
            variant={reason === entry.id ? 'primary' : 'secondary'}
            onPress={() => setReason(entry.id)}
          />
        ))}
      </View>
      <Input
        label={t('helpNearMe.reportDetails')}
        value={details}
        onChangeText={setDetails}
        accessibilityLabel={t('helpNearMe.reportDetails')}
      />
      {submitted ? (
        <Text style={styles.success}>{t('helpNearMe.reportThanks')}</Text>
      ) : (
        <Button
          title={reportMutation.isPending ? t('helpNearMe.reportSending') : t('helpNearMe.reportSubmit')}
          onPress={() => reportMutation.mutate()}
          disabled={reportMutation.isPending}
        />
      )}
      {reportMutation.error ? (
        <Text style={styles.error}>{hmoreErrorMessage(reportMutation.error)}</Text>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, marginBottom: theme.spacing.xs },
  meta: { fontFamily: FONT_MEDIUM, color: theme.colors.textMuted, marginBottom: theme.spacing.md },
  card: { marginBottom: theme.spacing.md },
  field: { marginBottom: theme.spacing.md },
  label: { fontFamily: FONT_BOLD, color: theme.colors.textMuted, marginBottom: 4, fontSize: 12 },
  value: { fontFamily: FONT_MEDIUM, color: theme.colors.text, lineHeight: 22 },
  missing: { color: theme.colors.textSecondary, fontStyle: 'italic' },
  section: { fontFamily: FONT_BOLD, color: theme.colors.text, marginTop: theme.spacing.lg, marginBottom: 6 },
  lead: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: theme.spacing.sm, lineHeight: 20 },
  reasons: { gap: 8, marginBottom: theme.spacing.md },
  success: { fontFamily: FONT_MEDIUM, color: theme.colors.secondary, marginTop: theme.spacing.sm },
  error: { fontFamily: FONT_MEDIUM, color: '#B42318', marginTop: theme.spacing.sm },
});
