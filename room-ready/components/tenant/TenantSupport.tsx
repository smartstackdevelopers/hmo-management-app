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
import { listOwnSupportPlans } from '@/lib/hmore/services/supportPlans';
import { getOwnProfile } from '@/lib/hmore/services/tenants';
import { getTimeline, listAppointments } from '@/lib/hmore/services/timeline';

export function TenantSupport() {
  const { hmore } = useAuth();
  const tenantQuery = useQuery({
    queryKey: ['hmore', 'tenant-me'],
    queryFn: getOwnProfile,
    enabled: hmore?.rbac.active_role === 'tenant',
  });
  const plansQuery = useQuery({
    queryKey: ['hmore', 'support-plans'],
    queryFn: listOwnSupportPlans,
  });
  const tenantId = tenantQuery.data?.id;
  const appointmentsQuery = useQuery({
    queryKey: ['hmore', 'appointments', tenantId],
    queryFn: () => listAppointments(tenantId!),
    enabled: !!tenantId,
  });
  const timelineQuery = useQuery({
    queryKey: ['hmore', 'timeline', tenantId],
    queryFn: () => getTimeline(tenantId!),
    enabled: !!tenantId,
  });

  if (tenantQuery.isLoading || plansQuery.isLoading) return <LoadingScreen message="Loading support..." />;
  const error = tenantQuery.error ?? plansQuery.error;
  if (error) {
    return <ErrorState message={hmoreErrorMessage(error, 'Could not load support')} onRetry={() => { tenantQuery.refetch(); plansQuery.refetch(); }} />;
  }

  const plans = plansQuery.data?.items ?? [];
  const appointments = appointmentsQuery.data?.items ?? [];
  const timeline = (timelineQuery.data?.items ?? []).filter((item) => item.can_view);

  return (
    <Screen
      refreshControl={
        <RefreshControl
          refreshing={plansQuery.isRefetching || appointmentsQuery.isRefetching}
          onRefresh={() => {
            tenantQuery.refetch();
            plansQuery.refetch();
            appointmentsQuery.refetch();
            timelineQuery.refetch();
          }}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <Text style={styles.lead}>Your support plan and appointments are read from your organisation. You cannot change the plan here.</Text>
      {!tenantId ? (
        <EmptyState title="No linked profile" message="Support plans appear when a tenant record is linked to this login." icon="people-outline" />
      ) : null}

      <SectionHeader title="Support plan" />
      {plans.length === 0 ? (
        <Text style={styles.empty}>No support plan is shared with you yet.</Text>
      ) : (
        plans.map((plan) => (
          <Card key={plan.id} style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.title}>{plan.title}</Text>
              <Badge label={plan.status} format={false} />
            </View>
            <Text style={styles.meta}>{plan.reference_number}</Text>
            {plan.tenant_summary ? <Text style={styles.body}>{plan.tenant_summary}</Text> : null}
            {plan.description ? <Text style={styles.body}>{plan.description}</Text> : null}
            {plan.planned_review_date ? (
              <Text style={styles.meta}>Review {formatUKDate(plan.planned_review_date)}</Text>
            ) : null}
          </Card>
        ))
      )}

      <SectionHeader title="Appointments" />
      {appointmentsQuery.error ? (
        <Text style={styles.empty}>{hmoreErrorMessage(appointmentsQuery.error, 'Appointments could not be loaded')}</Text>
      ) : appointments.length === 0 ? (
        <Text style={styles.empty}>No appointments.</Text>
      ) : (
        appointments.map((item) => (
          <Card key={item.id} style={styles.card}>
            <View style={styles.row}>
              <Text style={styles.title}>{item.title}</Text>
              <Badge label={item.status} format={false} />
            </View>
            <Text style={styles.meta}>
              {formatUKDate(item.starts_at)} · {item.appointment_kind}
              {item.location ? ` · ${item.location}` : ''}
            </Text>
            {item.description ? <Text style={styles.body}>{item.description}</Text> : null}
          </Card>
        ))
      )}

      <SectionHeader title="Recent activity" />
      {timelineQuery.error ? (
        <Text style={styles.empty}>{hmoreErrorMessage(timelineQuery.error, 'Activity could not be loaded')}</Text>
      ) : timeline.length === 0 ? (
        <Text style={styles.empty}>No recent activity you can view.</Text>
      ) : (
        timeline.map((item) => (
          <Card key={item.dedupe_key} style={styles.card}>
            <Text style={styles.title}>{item.title}</Text>
            <Text style={styles.meta}>
              {item.activity_type.replace(/_/g, ' ')} · {formatUKDate(item.occurred_at)}
              {item.status ? ` · ${item.status}` : ''}
            </Text>
            {item.summary ? <Text style={styles.body}>{item.summary}</Text> : null}
          </Card>
        ))
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  lead: { fontFamily: FONT_MEDIUM, fontSize: 14, lineHeight: 20, color: theme.colors.textSecondary, marginBottom: theme.spacing.md },
  empty: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, marginBottom: theme.spacing.md },
  card: { marginBottom: theme.spacing.sm },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 8, alignItems: 'center' },
  title: { fontFamily: FONT_BOLD, fontSize: 16, color: theme.colors.text, flex: 1 },
  meta: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted, marginTop: 6, textTransform: 'capitalize' },
  body: { fontFamily: FONT_SEMIBOLD, fontSize: 14, lineHeight: 20, color: theme.colors.textSecondary, marginTop: 8 },
});
