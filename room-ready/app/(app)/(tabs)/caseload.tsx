import { CaseloadList } from '@/components/staff/CaseloadList';
import { useAuth } from '@/contexts/AuthContext';
import { isSupportShellRole } from '@/lib/hmore/roles';

export default function CaseloadScreen() {
  const { hmore, user } = useAuth();
  if (!hmore || !isSupportShellRole(user?.role)) return null;
  return <CaseloadList />;
}
