import { IncidentDetail } from '@/components/staff/IncidentDetail';
import { useAuth } from '@/contexts/AuthContext';
import { isSupportShellRole } from '@/lib/hmore/roles';

export default function IncidentScreen() {
  const { hmore, user } = useAuth();
  if (!hmore || !isSupportShellRole(user?.role)) return null;
  return <IncidentDetail />;
}
