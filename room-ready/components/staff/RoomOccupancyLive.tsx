import { useQuery } from '@tanstack/react-query';

import { RecordCard, StaffPage } from '@/components/staff/ui';
import { ErrorState, LoadingScreen } from '@/components/ui/States';
import { hmoreErrorMessage } from '@/lib/hmore/client';
import { LIVE_OCCUPANCY_PRIVACY_NOTICE } from '@/lib/hmore/staff/occupancyView';
import {
  fetchRoomOccupancyDashboard,
  fetchRoomOccupancyRooms,
} from '@/lib/hmore/services/staff/roomOccupancy';

export function RoomOccupancyLive() {
  const query = useQuery({
    queryKey: ['hmore', 'staff', 'room-occupancy'],
    queryFn: async () => {
      const [dash, rooms] = await Promise.all([fetchRoomOccupancyDashboard(), fetchRoomOccupancyRooms()]);
      return { dash, rooms: rooms.items ?? [] };
    },
  });

  if (query.isLoading) return <LoadingScreen message="Loading occupancy..." />;
  if (query.isError) {
    return (
      <ErrorState
        message={hmoreErrorMessage(query.error, 'Could not load room occupancy')}
        onRetry={query.refetch}
      />
    );
  }

  const live = Boolean(query.data?.dash.live_counting_active);
  const rooms = query.data?.rooms ?? [];
  const notice = query.data?.dash.privacy_notice || LIVE_OCCUPANCY_PRIVACY_NOTICE;

  return (
    <StaffPage title="Room occupancy" subtitle={notice} onRefresh={query.refetch} refreshing={query.isRefetching}>
      <RecordCard
        title={live ? 'Live counting enabled' : 'Live counting disabled'}
        detail={
          live
            ? 'Showing estimated counts from approved edge devices only.'
            : 'Privacy approval gate incomplete or live counting not enabled. No camera streams are active.'
        }
      />
      {rooms.length === 0 ? (
        <RecordCard title="No room counts" detail="No occupancy states are available for your organisation." />
      ) : null}
      {rooms.map((room) => (
        <RecordCard
          key={room.room_id}
          title={`${room.property_name || 'Property'} · ${room.room_label || room.room_id}`}
          status={room.occupancy_status || 'offline'}
          detail={[
            room.occupancy_status === 'offline'
              ? 'Count unavailable (offline)'
              : `${room.estimated_count_label || 'Estimated'}: ${room.estimated_count ?? '—'} / ${room.max_capacity ?? '—'}`,
            `Equipment: ${room.device_connection_status || 'unknown'}`,
            room.last_updated_at ? `Updated ${room.last_updated_at}` : null,
          ]
            .filter(Boolean)
            .join(' · ')}
        />
      ))}
    </StaffPage>
  );
}
