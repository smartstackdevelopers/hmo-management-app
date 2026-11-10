import { IncidentBoard } from '@/components/staff/IncidentBoard';
import { useAuth } from '@/contexts/AuthContext';
import { isSupportShellRole } from '@/lib/hmore/roles';

export default function IncidentsScreen() {
  const { hmore, user } = useAuth();
  if (!hmore || !isSupportShellRole(user?.role)) return null;
  return <IncidentBoard />;
}
