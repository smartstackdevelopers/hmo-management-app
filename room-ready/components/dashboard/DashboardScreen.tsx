import { RefreshControl } from 'react-native';

import { ActivityFeed } from '@/components/dashboard/ActivityFeed';
import { ComplianceOverviewCard } from '@/components/dashboard/ComplianceOverviewCard';
import { DashboardOverview } from '@/components/dashboard/DashboardOverview';
import { PortfolioHomeCard } from '@/components/dashboard/PortfolioHomeCard';
import { PropertySnapshotRow } from '@/components/dashboard/PropertySnapshotRow';
import { TenantHomeCard } from '@/components/dashboard/TenantHomeCard';
import { NextSteps, buildDashboardTodos } from '@/components/ui/NextSteps';
import { Screen } from '@/components/ui/Screen';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { theme } from '@/constants/theme';
import { useAuth } from '@/contexts/AuthContext';
import { useDashboard, useMarkNotificationRead, useProperties, useTenancies } from '@/hooks/useApi';
import { assessPropertyCompliance } from '@/lib/compliance';
import { navigateFromNotification } from '@/lib/notificationNavigation';
import { router } from 'expo-router';

export default function DashboardScreen() {
  const { user } = useAuth();
  const { data, isLoading, error, refetch, isRefetching } = useDashboard();
  const { data: propertiesData } = useProperties();
  const { data: tenanciesData } = useTenancies();
  const markRead = useMarkNotificationRead();

  if (isLoading) return <LoadingScreen message="Loading..." />;
  if (error || !data) {
    return <ErrorState message="Could not load your home screen." onRetry={refetch} />;
  }

  const { stats, expiringDocuments, notifications } = data;
  const role = user?.role;
  if (!role) return <ErrorState message="Your account could not be loaded." onRetry={refetch} />;

  const properties = propertiesData?.properties ?? [];
  const complianceReports = properties.map((p) => assessPropertyCompliance(p));
  const portfolioScore =
    complianceReports.length > 0
      ? Math.round(complianceReports.reduce((s, r) => s + r.score, 0) / complianceReports.length)
      : null;
  const criticalGaps = complianceReports.reduce(
    (sum, r) => sum + r.checks.filter((c) => c.status === 'non_compliant').length,
    0
  );

  const unreadCount = notifications.filter((n) => !n.read).length;
  const attentionCount = getAttentionCount(role, stats, criticalGaps);
  const status = getStatus(attentionCount, portfolioScore, criticalGaps, role);
  const tenantTenancy =
    tenanciesData?.tenancies?.find((t) => t.status === 'active') ?? tenanciesData?.tenancies?.[0];
  const tenantHome = tenantTenancy?.room?.property;
  const isPortfolioRole = role === 'landlord' || role === 'property_manager';
  const subtitle =
    role === 'tenant' && tenantHome
      ? `Your home · ${tenantHome.name}`
      : getHeroSubtitle(role, stats, portfolioScore);
  const todos = buildDashboardTodos({
    role,
    expiringDocuments,
    openMaintenance: Number(stats.openMaintenance ?? stats.openRepairs ?? 0),
    expiringDocsCount: Number(stats.expiringDocs ?? 0),
    hasTenancy: !!stats.hasTenancy,
    inspectionsDue: Number(stats.inspectionsDue ?? 0),
    pendingApplications: Number(stats.pendingApplications ?? 0),
    propertiesCount: properties.length,
    criticalGaps,
    portfolioScore,
  });

  function handleNotificationPress(n: (typeof notifications)[0]) {
    if (!n.read) markRead.mutate(n.id);
    navigateFromNotification(n);
  }

  return (
    <Screen
      fullBleedHeader
      style={{ backgroundColor: theme.colors.backgroundAlt }}
      refreshControl={
        <RefreshControl refreshing={isRefetching} onRefresh={refetch} tintColor={theme.colors.secondary} />
      }
      header={
        <DashboardOverview
          firstName={user?.firstName ?? 'there'}
          lastName={user?.lastName}
          role={role}
          subtitle={subtitle}
          status={status}
          unreadCount={unreadCount}
        />
      }
      contentContainerStyle={{ paddingTop: 0 }}
    >
      {role === 'tenant' && tenantTenancy ? <TenantHomeCard tenancy={tenantTenancy} /> : null}

      {isPortfolioRole ? (
        <PortfolioHomeCard
          properties={properties}
          portfolioScore={portfolioScore}
          openRepairs={Number(stats.openMaintenance ?? 0)}
          expiringDocs={Number(stats.expiringDocs ?? 0)}
        />
      ) : null}

      {isPortfolioRole && portfolioScore !== null ? (
        <ComplianceOverviewCard
          score={portfolioScore}
          criticalGaps={criticalGaps}
          onPress={() => router.push('/(app)/(tabs)/compliance')}
        />
      ) : null}

      {isPortfolioRole && properties.length > 0 ? <PropertySnapshotRow properties={properties} /> : null}

      <NextSteps items={todos} />

      <ActivityFeed
        notifications={notifications}
        onSeeAllNotifications={() => router.push('/(app)/notifications')}
        onNotificationPress={handleNotificationPress}
      />
    </Screen>
  );
}

function getAttentionCount(role: string, stats: Record<string, number | string>, criticalGaps: number): number {
  if (role === 'landlord' || role === 'property_manager') {
    return (
      Number(stats.expiringDocs ?? 0) +
      Number(stats.openMaintenance ?? 0) +
      Number(stats.inspectionsDue ?? 0) +
      criticalGaps
    );
  }
  if (role === 'tenant') {
    return Number(stats.openRepairs ?? 0) + Number(stats.pendingApplications ?? 0);
  }
  return Number(stats.openMaintenance ?? stats.openRepairs ?? stats.activeJobs ?? 0);
}

function getStatus(
  attentionCount: number,
  portfolioScore: number | null,
  criticalGaps: number,
  role: string
): { label: string; tone: 'success' | 'warning' | 'error' | 'neutral' } {
  if (attentionCount > 0) {
    return {
      label: `${attentionCount} to do`,
      tone: criticalGaps > 0 || attentionCount > 2 ? 'error' : 'warning',
    };
  }
  if (portfolioScore !== null && portfolioScore < 75 && (role === 'landlord' || role === 'property_manager')) {
    return { label: 'Checks need work', tone: 'warning' };
  }
  return { label: 'All clear', tone: 'success' };
}

function getHeroSubtitle(role: string, stats: Record<string, number | string>, portfolioScore: number | null): string {
  if (role === 'landlord') {
    const count = Number(stats.properties ?? 0);
    if (count === 0) return 'Add your first property to get started';
    if (portfolioScore !== null) return `${count} propert${count === 1 ? 'y' : 'ies'} · ${portfolioScore}% checks score`;
    return `${count} propert${count === 1 ? 'y' : 'ies'}`;
  }
  if (role === 'tenant') {
    return stats.hasTenancy ? 'Your tenancy at a glance' : 'Find a room and apply in a few taps';
  }
  if (role === 'property_manager') {
    const count = Number(stats.managedProperties ?? 0);
    return count > 0 ? `${count} managed propert${count === 1 ? 'y' : 'ies'}` : 'Your portfolio overview';
  }
  if (role === 'contractor') {
    const jobs = Number(stats.activeJobs ?? 0);
    return jobs > 0 ? `${jobs} active job${jobs === 1 ? '' : 's'}` : 'No jobs scheduled';
  }
  return 'Platform overview';
}
