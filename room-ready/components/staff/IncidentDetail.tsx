import { useQuery } from '@tanstack/react-query';
import { useLocalSearchParams } from 'expo-router';

import { RecordCard, StaffPage } from '@/components/staff/ui';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { getIncident } from '@/lib/hmore/services/staff/incidents';

export function IncidentDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const query = useQuery({
    queryKey: ['hmore', 'staff', 'incident', id],
    queryFn: () => getIncident(id),
    enabled: !!id,
  });

  if (query.isLoading) return <LoadingScreen message="Loading incident..." />;
  if (query.isError || !query.data) {
    return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load this incident')} onRetry={query.refetch} />;
  }

  const incident = query.data;
  return (
    <StaffPage title={incident.reference_number} subtitle={incident.title} onRefresh={query.refetch} refreshing={query.isRefetching}>
      <RecordCard title="Status" status={incident.status} detail={`${incident.severity} · ${formatUKDate(incident.occurred_at)}`} />
      <RecordCard title="Description" detail={incident.description} />
      {incident.location ? <RecordCard title="Location" detail={incident.location} /> : null}
    </StaffPage>
  );
}
