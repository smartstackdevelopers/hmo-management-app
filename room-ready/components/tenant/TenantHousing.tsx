import { useQuery } from '@tanstack/react-query';
import { RefreshControl, StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Screen, SectionHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useI18n } from '@/hooks/useI18n';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { formatAssignedAddress, getOwnHousing } from '@/lib/hmore/services/housing';
import { listHousingApplications } from '@/lib/hmore/services/housingApplications';

export function TenantHousing() {
  const { t, fontScale, prefs } = useI18n();
  const housingQuery = useQuery({
    queryKey: ['hmore', 'tenant-housing'],
    queryFn: getOwnHousing,
  });
  const appsQuery = useQuery({
    queryKey: ['hmore', 'housing-applications'],
    queryFn: listHousingApplications,
  });

  if (housingQuery.isLoading || appsQuery.isLoading) return <LoadingScreen message={t('housing.loading')} />;
  const error = housingQuery.error ?? appsQuery.error;
  if (error) {
    return (
      <ErrorState
        message={hmoreErrorMessage(error, t('housing.error'))}
        onRetry={() => {
          housingQuery.refetch();
          appsQuery.refetch();
        }}
      />
    );
  }

  const housing = housingQuery.data;
  const applications = appsQuery.data?.items ?? [];
  const address = formatAssignedAddress(housing);
  const contrast = prefs.highContrast;

  return (
    <Screen
      style={contrast ? styles.contrast : undefined}
      refreshControl={
        <RefreshControl
          refreshing={housingQuery.isRefetching || appsQuery.isRefetching}
          onRefresh={() => {
            housingQuery.refetch();
            appsQuery.refetch();
          }}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <Text style={[styles.note, { fontSize: 14 * fontScale }, contrast && styles.contrastText]}>{t('housing.intro')}</Text>
      {!housing ? (
        <EmptyState title={t('housing.noProfileTitle')} message={t('housing.noProfile')} icon="home-outline" />
      ) : (
        <Card style={contrast ? styles.contrastCard : undefined}>
          <View style={styles.header}>
            <Text style={[styles.name, contrast && styles.contrastText, { fontSize: 20 * fontScale }]}>
              {housing.property?.name || t('housing.property')}
            </Text>
            <Badge label={housing.status} variant={housing.status === 'active' ? 'success' : 'default'} format={false} />
          </View>
          <Row label={t('housing.reference')} value={housing.tenancy_reference} empty={t('housing.notRecorded')} />
          <Row label={t('housing.status')} value={housing.status} empty={t('housing.notRecorded')} />
          {housing.property && address ? (
            <>
              <Row label={t('housing.property')} value={address} empty={t('housing.notRecorded')} />
              {housing.room ? (
                <Row
                  label={t('housing.room')}
                  value={[housing.room.label, housing.room.floor_label ? `${t('housing.floor')} ${housing.room.floor_label}` : null]
                    .filter(Boolean)
                    .join(' · ')}
                  empty={t('housing.notRecorded')}
                />
              ) : null}
            </>
          ) : (
            <Text style={[styles.unassigned, { fontSize: 16 * fontScale }]}>{t('housing.unassigned')}</Text>
          )}
        </Card>
      )}

      <SectionHeader title={t('housing.applications')} />
      {applications.length === 0 ? (
        <Text style={styles.empty}>{t('housing.noApplications')}</Text>
      ) : (
        applications.map((app) => (
          <Card key={app.id} style={styles.app}>
            <View style={styles.header}>
              <Text style={styles.appTitle}>{app.reference_number}</Text>
              <Badge label={app.status} format={false} />
            </View>
            <Text style={styles.body}>{app.housing_requirements}</Text>
            <Text style={styles.meta}>
              {app.accommodation_type || t('housing.accommodationUnset')}
              {app.submitted_at ? ` · ${t('housing.submitted')} ${formatUKDate(app.submitted_at)}` : ''}
            </Text>
            {app.on_waiting_list ? (
              <Text style={styles.meta}>
                {t('housing.waiting')}
                {app.waiting_list_position ? ` · ${t('housing.position')} ${app.waiting_list_position}` : ''}
              </Text>
            ) : null}
            {app.information_required_notes ? (
              <Text style={styles.warn}>
                {t('housing.information')}: {app.information_required_notes}
              </Text>
            ) : null}
          </Card>
        ))
      )}
    </Screen>
  );
}

function Row({ label, value, empty }: { label: string; value: string | null; empty: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value?.trim() ? value : empty}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  contrastCard: { borderWidth: 2, borderColor: '#000000' },
  note: {
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    lineHeight: 20,
    marginBottom: theme.spacing.md,
  },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 8 },
  name: { fontFamily: FONT_BOLD, color: theme.colors.text, flex: 1 },
  unassigned: { fontFamily: FONT_SEMIBOLD, color: theme.colors.text, marginTop: 12 },
  row: { marginTop: 10 },
  label: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted },
  value: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text, marginTop: 2 },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: theme.spacing.md },
  app: { marginBottom: theme.spacing.sm },
  appTitle: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text, flex: 1 },
  body: { fontFamily: FONT_MEDIUM, fontSize: 14, lineHeight: 20, color: theme.colors.textSecondary },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6 },
  warn: { fontFamily: FONT_MEDIUM, fontSize: 13, color: theme.colors.warning, marginTop: 8 },
});
