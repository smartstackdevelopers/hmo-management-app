import { router } from 'expo-router';
import { RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { StatCard } from '@/components/ui/StatCard';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { theme } from '@/constants/theme';
import { UK_CONFIG } from '@/constants/uk';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useAdminAnalytics } from '@/hooks/useApi';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function SettingsScreen() {
  const guard = useRoleGuard(TAB_ROLES.settings);
  if (guard) return guard;

  const { signOut } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useAdminAnalytics();

  if (isLoading) return <LoadingScreen />;
  if (error) return <ErrorState message="Could not load platform data" onRetry={refetch} />;

  const analytics = (data?.analytics ?? {}) as Record<string, unknown>;
  const usersByRole = analytics.usersByRole as Record<string, number> | undefined;

  async function handleSignOut() {
    await signOut();
    router.replace('/(auth)/welcome');
  }

  return (
    <ScrollView
      style={styles.container}
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />}
    >
      <Text style={styles.title}>Platform</Text>
      <Text style={styles.subtitle}>Room Ready administration · {UK_CONFIG.country}</Text>

      <View style={styles.grid}>
        <StatCard label="Total Users" value={String(analytics.totalUsers ?? 0)} icon="people-outline" style={styles.stat} />
        <StatCard label="Active Listings" value={String(analytics.activeListings ?? 0)} icon="list-outline" variant="info" style={styles.stat} />
        <StatCard label="Unverified" value={String(analytics.pendingVerification ?? 0)} icon="shield-outline" variant="warning" style={styles.stat} />
        <StatCard label="Open Repairs" value={String(analytics.openMaintenance ?? 0)} icon="construct-outline" style={styles.stat} />
      </View>

      {usersByRole && (
        <Card style={styles.section}>
          <Text style={styles.sectionTitle}>Users by Role</Text>
          {Object.entries(usersByRole).map(([role, count]) => (
            <View key={role} style={styles.roleRow}>
              <Text style={styles.roleName}>{role.replace(/_/g, ' ')}</Text>
              <Text style={styles.roleCount}>{count}</Text>
            </View>
          ))}
        </Card>
      )}

      <Card style={styles.section}>
        <Text style={styles.sectionTitle}>Configuration</Text>
        <Text style={styles.setting}>Region: {UK_CONFIG.country}</Text>
        <Text style={styles.setting}>Currency: {UK_CONFIG.currency} ({UK_CONFIG.currencySymbol})</Text>
        <Text style={styles.setting}>Compliance reminders: Enabled</Text>
      </Card>

      <Button title="Sign Out" variant="outline" onPress={handleSignOut} fullWidth />
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: theme.colors.background },
  content: { padding: theme.spacing.md, paddingBottom: 40 },
  title: { ...theme.typography.h1, color: theme.colors.text },
  subtitle: { color: theme.colors.textSecondary, marginBottom: theme.spacing.lg, marginTop: 4 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: theme.spacing.sm, marginBottom: theme.spacing.lg },
  stat: { width: '48%', flexGrow: 1 },
  section: { marginBottom: theme.spacing.md },
  sectionTitle: { fontWeight: '700', marginBottom: 12, color: theme.colors.text, fontSize: 16 },
  roleRow: { flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 10, borderBottomWidth: 1, borderBottomColor: theme.colors.borderLight },
  roleName: { textTransform: 'capitalize', color: theme.colors.textSecondary },
  roleCount: { fontWeight: '700', color: theme.colors.text },
  setting: { color: theme.colors.textSecondary, paddingVertical: 6, fontSize: 15 },
});
