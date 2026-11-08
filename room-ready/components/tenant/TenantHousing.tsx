import { useQuery } from '@tanstack/react-query';
import { RefreshControl, StyleSheet, Text, View } from 'react-native';

import { Badge } from '@/components/ui/Badge';
import { Card } from '@/components/ui/Card';
import { Screen, SectionHeader } from '@/components/ui/Screen';
import { EmptyState, ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listHousingApplications } from '@/lib/hmore/services/housingApplications';
import { getOwnTenant } from '@/lib/hmore/services/tenants';

export function TenantHousing() {
  const { hmore } = useAuth();
  const userId = hmore?.auth.id ?? '';
  const tenantQuery = useQuery({
    queryKey: ['hmore', 'tenant', userId],
    queryFn: () => getOwnTenant(userId),
    enabled: !!userId,
  });
  const appsQuery = useQuery({
    queryKey: ['hmore', 'housing-applications'],
    queryFn: listHousingApplications,
  });

  if (tenantQuery.isLoading || appsQuery.isLoading) return <LoadingScreen message="Loading your housing..." />;
  const error = tenantQuery.error ?? appsQuery.error;
  if (error) {
    return (
      <ErrorState
        message={hmoreErrorMessage(error, 'Could not load housing')}
        onRetry={() => {
          tenantQuery.refetch();
          appsQuery.refetch();
        }}
      />
    );
  }

  const tenant = tenantQuery.data;
  const applications = appsQuery.data?.items ?? [];

  return (
    <Screen
      refreshControl={
        <RefreshControl
          refreshing={tenantQuery.isRefetching || appsQuery.isRefetching}
          onRefresh={() => {
            tenantQuery.refetch();
            appsQuery.refetch();
          }}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <Text style={styles.note}>
        This is your organisation housing record. Tenants cannot edit it in the app.
      </Text>
      {!tenant ? (
        <EmptyState
          title="No housing record"
          message="When your organisation links a tenant profile to this login, it will show here."
          icon="home-outline"
        />
      ) : (
        <Card>
          <View style={styles.header}>
            <Text style={styles.name}>{tenant.preferred_name}</Text>
            <Badge label={tenant.status} variant={tenant.status === 'active' ? 'success' : 'default'} format={false} />
          </View>
          <Row label="Full name" value={tenant.full_name} />
          <Row label="Email" value={tenant.email} />
          <Row label="Phone" value={tenant.phone} />
          <Row label="Tenancy reference" value={tenant.tenancy_reference} />
          <Row label="Needs and goals" value={tenant.needs_goals} />
          <Row label="Preferences" value={tenant.preferences} />
        </Card>
      )}

      <SectionHeader title="Housing applications" />
      {applications.length === 0 ? (
        <Text style={styles.empty}>No applications are linked to you.</Text>
      ) : (
        applications.map((app) => (
          <Card key={app.id} style={styles.app}>
            <View style={styles.header}>
              <Text style={styles.appTitle}>{app.reference_number}</Text>
              <Badge label={app.status} format={false} />
            </View>
            <Text style={styles.body}>{app.housing_requirements}</Text>
            <Text style={styles.meta}>
              {app.accommodation_type || 'Accommodation type not set'}
              {app.submitted_at ? ` · Submitted ${formatUKDate(app.submitted_at)}` : ''}
            </Text>
            {app.on_waiting_list ? (
              <Text style={styles.meta}>
                Waiting list{app.waiting_list_position ? ` · position ${app.waiting_list_position}` : ''}
              </Text>
            ) : null}
            {app.information_required_notes ? (
              <Text style={styles.warn}>Information requested: {app.information_required_notes}</Text>
            ) : null}
          </Card>
        ))
      )}
    </Screen>
  );
}

function Row({ label, value }: { label: string; value: string | null }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text style={styles.value}>{value?.trim() ? value : 'Not recorded'}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  note: {
    fontFamily: FONT_MEDIUM,
    color: theme.colors.textSecondary,
    fontSize: 14,
    lineHeight: 20,
    marginBottom: theme.spacing.md,
  },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8, marginBottom: 8 },
  name: { fontFamily: FONT_BOLD, fontSize: 20, color: theme.colors.text, flex: 1 },
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
