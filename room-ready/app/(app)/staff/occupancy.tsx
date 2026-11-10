import { OccupancySurveys } from '@/components/staff/OccupancySurveys';
import { useAuth } from '@/contexts/AuthContext';
import { isSupportShellRole } from '@/lib/hmore/roles';

export default function OccupancyScreen() {
  const { hmore, user } = useAuth();
  if (!hmore || !isSupportShellRole(user?.role)) return null;
  return <OccupancySurveys />;
}
