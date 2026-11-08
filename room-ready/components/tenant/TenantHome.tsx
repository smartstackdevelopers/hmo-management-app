import { useQuery } from '@tanstack/react-query';
import { router } from 'expo-router';
import { RefreshControl, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { FONT_BOLD, FONT_MEDIUM, FONT_SEMIBOLD } from '@/constants/fonts';
import { formatUKDate } from '@/constants/uk';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useAccessibilityPrefs } from '@/hooks/useAccessibilityPrefs';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listMaintenance } from '@/lib/hmore/services/maintenance';
import { getOwnTenant } from '@/lib/hmore/services/tenants';
import { listAppointments } from '@/lib/hmore/services/timeline';

const CLOSED = new Set(['completed', 'closed', 'cancelled']);

export function TenantHome() {
  const { user, hmore } = useAuth();
  const { prefs, fontScale } = useAccessibilityPrefs();
  const userId = hmore?.auth.id ?? '';
  const tenantQuery = useQuery({
    queryKey: ['hmore', 'tenant', userId],
    queryFn: () => getOwnTenant(userId),
    enabled: !!userId,
  });
  const repairsQuery = useQuery({
    queryKey: ['hmore', 'maintenance'],
    queryFn: () => listMaintenance({ page: 1, page_size: 50 }),
  });
  const tenantId = tenantQuery.data?.id;
  const appointmentsQuery = useQuery({
    queryKey: ['hmore', 'appointments', tenantId],
    queryFn: () => listAppointments(tenantId!),
    enabled: !!tenantId,
  });

  const loading = tenantQuery.isLoading || repairsQuery.isLoading;
  const error = tenantQuery.error ?? repairsQuery.error;
  if (loading) return <LoadingScreen message="Loading your home..." />;
  if (error) {
    return (
      <ErrorState
        message={hmoreErrorMessage(error, 'Could not load your home')}
        onRetry={() => {
          tenantQuery.refetch();
          repairsQuery.refetch();
        }}
      />
    );
  }

  const tenant = tenantQuery.data;
  const openRepairs = (repairsQuery.data?.items ?? []).filter((row) => !CLOSED.has(row.status)).length;
  const nextAppointment = (appointmentsQuery.data?.items ?? [])
    .filter((row) => row.status !== 'cancelled' && new Date(row.starts_at).getTime() >= Date.now())
    .sort((a, b) => new Date(a.starts_at).getTime() - new Date(b.starts_at).getTime())[0];
  const contrast = prefs.highContrast;
  const titleSize = 28 * fontScale;

  return (
    <Screen
      style={contrast ? styles.contrast : undefined}
      refreshControl={
        <RefreshControl
          refreshing={tenantQuery.isRefetching || repairsQuery.isRefetching}
          onRefresh={() => {
            tenantQuery.refetch();
            repairsQuery.refetch();
            if (tenantId) appointmentsQuery.refetch();
          }}
          tintColor={theme.colors.secondary}
        />
      }
    >
      <Text style={[styles.kicker, contrast && styles.contrastText]}>Hello</Text>
      <Text style={[styles.title, contrast && styles.contrastText, { fontSize: titleSize }]}>
        {tenant?.preferred_name || user?.firstName || 'there'}
      </Text>
      <Text style={[styles.lead, contrast && styles.contrastMuted]}>
        Your housing record is read-only here. Ask your organisation if a detail needs changing.
      </Text>

      <Card style={contrast ? styles.contrastCard : undefined}>
        <Text style={styles.section}>Housing</Text>
        {tenant ? (
          <>
            <Fact label="Name" value={tenant.full_name || tenant.preferred_name} />
            <Fact label="Reference" value={tenant.tenancy_reference || 'Not recorded'} />
            <Fact label="Status" value={tenant.status} />
          </>
        ) : (
          <Text style={styles.muted}>No housing record is linked to this login yet.</Text>
        )}
        <Button title="My home" variant="outline" onPress={() => router.push('/(app)/(tabs)/tenancy')} fullWidth style={styles.button} />
      </Card>

      <View style={styles.stats}>
        <Card style={styles.stat}>
          <Text style={styles.statValue}>{openRepairs}</Text>
          <Text style={styles.statLabel}>Open repairs</Text>
        </Card>
        <Card style={styles.stat}>
          <Text style={styles.statValue}>{nextAppointment ? formatUKDate(nextAppointment.starts_at) : 'None'}</Text>
          <Text style={styles.statLabel}>{nextAppointment?.title || 'Next appointment'}</Text>
        </Card>
      </View>

      <Button title="Report a repair" onPress={() => router.push('/(app)/maintenance/new')} fullWidth />
      <View style={styles.row}>
        <Button title="Support" variant="outline" onPress={() => router.push('/(app)/(tabs)/support')} style={styles.half} />
        <Button title="Assistant" variant="outline" onPress={() => router.push('/(app)/assistant')} style={styles.half} />
      </View>
    </Screen>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.fact}>
      <Text style={styles.factLabel}>{label}</Text>
      <Text style={styles.factValue}>{value}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  contrast: { backgroundColor: '#FFFFFF' },
  contrastText: { color: '#000000' },
  contrastMuted: { color: '#111111' },
  contrastCard: { borderWidth: 2, borderColor: '#000000' },
  kicker: { fontFamily: FONT_SEMIBOLD, color: theme.colors.secondaryDark, fontSize: 13 },
  title: { fontFamily: FONT_BOLD, color: theme.colors.text, letterSpacing: -0.5, marginTop: 2 },
  lead: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 14, lineHeight: 20, marginTop: 6, marginBottom: theme.spacing.md },
  section: { fontFamily: FONT_SEMIBOLD, fontSize: 16, color: theme.colors.text, marginBottom: theme.spacing.sm },
  muted: { fontFamily: FONT_MEDIUM, color: theme.colors.textSecondary, fontSize: 14 },
  fact: { marginBottom: 8 },
  factLabel: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textMuted },
  factValue: { fontFamily: FONT_SEMIBOLD, fontSize: 15, color: theme.colors.text, textTransform: 'capitalize' },
  button: { marginTop: theme.spacing.sm },
  stats: { flexDirection: 'row', gap: theme.spacing.sm, marginVertical: theme.spacing.md },
  stat: { flex: 1 },
  statValue: { fontFamily: FONT_BOLD, fontSize: 18, color: theme.colors.text },
  statLabel: { fontFamily: FONT_MEDIUM, fontSize: 12, color: theme.colors.textSecondary, marginTop: 4 },
  row: { flexDirection: 'row', gap: theme.spacing.sm, marginTop: theme.spacing.sm },
  half: { flex: 1 },
});
