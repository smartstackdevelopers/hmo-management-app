import { ApprovalInbox } from '@/components/staff/ApprovalInbox';
import { useAuth } from '@/contexts/AuthContext';
import { hasPermission, isSupportShellRole } from '@/lib/hmore/roles';

export default function ApprovalsScreen() {
  const { hmore, user } = useAuth();
  const allowed = !!hmore && isSupportShellRole(user?.role) && hasPermission(hmore.rbac.permissions, 'approvals.inbox.read');
  if (!allowed) return null;
  return <ApprovalInbox />;
}
