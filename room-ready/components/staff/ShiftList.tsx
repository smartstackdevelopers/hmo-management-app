import { useQuery } from '@tanstack/react-query';

import { RecordCard, StaffPage } from '@/components/staff/ui';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { formatUKDate } from '@/constants/uk';
import { useAuth } from '@/contexts/AuthContext';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { listOwnShifts } from '@/lib/hmore/services/staff/shifts';

export function ShiftList() {
  const { user } = useAuth();
  const query = useQuery({
    queryKey: ['hmore', 'staff', 'shifts', user?.id],
    queryFn: () => listOwnShifts(user?.id || ''),
    enabled: !!user?.id,
  });

  if (query.isLoading) return <LoadingScreen message="Loading shifts..." />;
  if (query.isError) return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load shifts')} onRetry={query.refetch} />;

  const items = query.data?.items ?? [];
  return (
    <StaffPage title="Shifts" subtitle="Your own shifts from the rota." onRefresh={query.refetch} refreshing={query.isRefetching}>
      {items.length === 0 ? <RecordCard title="No shifts" detail="Nothing was returned for your user." /> : null}
      {items.map((shift) => (
        <RecordCard
          key={shift.id}
          title={`${formatUKDate(shift.starts_at)} · ${shift.shift_type}`}
          status={shift.status}
          detail={[shift.location, shift.notes].filter(Boolean).join(' · ') || shift.timezone}
        />
      ))}
    </StaffPage>
  );
}
