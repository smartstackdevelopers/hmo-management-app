import { useQuery } from '@tanstack/react-query';
import { router, useLocalSearchParams } from 'expo-router';
import { useLayoutEffect } from 'react';
import { useNavigation } from 'expo-router';

import { FactGrid } from '@/components/dashboard/mobileChrome';
import { BackLink, StaffPage, Timeline, staffLabel, statusTone } from '@/components/staff/ui';
import { Button } from '@/components/ui/Button';
import { Chip } from '@/components/ui/Chip';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getCaseDetail } from '@/lib/hmore/services/staff/caseload';

export function CaseDetail() {
  const navigation = useNavigation();
  const { tenantId } = useLocalSearchParams<{ tenantId: string }>();
  const { user } = useAuth();
  const query = useQuery({
    queryKey: ['hmore', 'staff', 'case', tenantId, user?.role],
    queryFn: () => getCaseDetail(user?.role, tenantId),
    enabled: !!tenantId,
  });

  useLayoutEffect(() => {
    navigation.setOptions({ headerShown: false });
  }, [navigation]);

  if (query.isLoading) return <LoadingScreen message="Loading tenant..." />;
  if (query.isError) return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load this tenant')} onRetry={query.refetch} />;

  const detail = query.data;
  const tenant = detail?.tenant;
  const name = tenant?.preferred_name || tenant?.full_name || 'Tenant';
  const facts = [
    tenant?.tenancy_reference ? { label: 'Reference', value: tenant.tenancy_reference } : null,
    tenant?.status ? { label: 'Status', value: staffLabel(tenant.status) } : null,
    { label: 'Recent logs', value: String(detail?.recent_logs.length ?? 0) },
    { label: 'Handovers', value: String(detail?.recent_handovers.length ?? 0) },
  ].filter((item): item is { label: string; value: string } => !!item);

  const timeline = [
    ...(detail?.recent_logs ?? []).map((log) => ({
      key: `log-${log.id}`,
      title: log.summary,
      meta: [log.log_date ? formatUKDate(log.log_date) : null, staffLabel(log.activity_category)].filter(Boolean).join(' · '),
    })),
    ...(detail?.recent_handovers ?? []).map((handover) => ({
      key: `handover-${handover.id}`,
      title: handover.summary,
      meta: staffLabel(handover.status),
    })),
  ];

  return (
    <StaffPage title={name} subtitle={tenant?.tenancy_reference || undefined} leading={<BackLink />} onRefresh={query.refetch} refreshing={query.isRefetching}>
      {tenant?.status ? <Chip label={staffLabel(tenant.status)} tone={statusTone(tenant.status)} /> : null}
      <FactGrid items={facts} />
      <Timeline items={timeline} />
      <Button title="Add daily log" onPress={() => router.push('/(app)/(tabs)/notes')} fullWidth />
    </StaffPage>
  );
}
