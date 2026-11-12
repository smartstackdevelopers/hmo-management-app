import { hmoreFetch } from '@/lib/hmore/client';

export type RoomOccupancyRow = {
  room_id: string;
  room_label?: string | null;
  property_name?: string | null;
  estimated_count?: number | null;
  max_capacity?: number | null;
  occupancy_status?: string | null;
  device_connection_status?: string | null;
  last_updated_at?: string | null;
  estimated_count_label?: string | null;
};

export async function fetchRoomOccupancyDashboard() {
  return hmoreFetch<{
    live_counting_active?: boolean;
    approval_gate?: Record<string, unknown>;
    privacy_notice?: string;
    rooms?: RoomOccupancyRow[];
  }>('/room-occupancy/dashboard', { method: 'GET' });
}

export async function fetchRoomOccupancyRooms() {
  return hmoreFetch<{ items: RoomOccupancyRow[] }>('/room-occupancy/rooms', { method: 'GET' });
}
