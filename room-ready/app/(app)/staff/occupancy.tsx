import { OccupancySurveys } from '@/components/staff/OccupancySurveys';
import { RoomOccupancyLive } from '@/components/staff/RoomOccupancyLive';
import { useAuth } from '@/contexts/AuthContext';
import { hasPermission, isSupportShellRole } from '@/lib/hmore/roles';

export default function OccupancyScreen() {
  const { hmore, user } = useAuth();
  if (!hmore || !isSupportShellRole(user?.role)) return null;

  const canReadLive = hasPermission(hmore.rbac?.permissions, 'occupancy.read');
  // Tenants never reach staff shell; landlords without occupancy.read stay on surveys only.
  if (canReadLive) {
    return <RoomOccupancyLive />;
  }
  return <OccupancySurveys />;
}
