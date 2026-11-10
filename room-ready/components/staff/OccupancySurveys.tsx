import { useQuery } from '@tanstack/react-query';

import { RecordCard, StaffPage } from '@/components/staff/ui';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { OCCUPANCY_PHASE6_NOTICE } from '@/lib/hmore/staff/occupancyView';
import { listOccupancySurveys } from '@/lib/hmore/services/staff/occupancy';

export function OccupancySurveys() {
  const query = useQuery({ queryKey: ['hmore', 'staff', 'occupancy-surveys'], queryFn: listOccupancySurveys });

  if (query.isLoading) return <LoadingScreen message="Loading surveys..." />;
  if (query.isError) return <ErrorState message={hmoreErrorMessage(query.error, 'Could not load occupancy surveys')} onRetry={query.refetch} />;

  const surveys = query.data ?? [];
  return (
    <StaffPage title="Occupancy" subtitle={OCCUPANCY_PHASE6_NOTICE} onRefresh={query.refetch} refreshing={query.isRefetching}>
      {surveys.length === 0 ? (
        <RecordCard title="No surveys" detail="No occupancy site surveys were returned. A people count is not shown." />
      ) : null}
      {surveys.map((survey) => (
        <RecordCard
          key={survey.id}
          title={survey.feasibility_status || survey.status}
          status={survey.status}
          detail={[survey.survey_date, survey.feasibility_summary].filter(Boolean).join(' · ') || 'Survey summary from the server.'}
        />
      ))}
    </StaffPage>
  );
}
