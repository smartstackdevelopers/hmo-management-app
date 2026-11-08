import { TenantSupport } from '@/components/tenant/TenantSupport';
import { EmptyState } from '@/components/ui/States';
import { TAB_ROLES } from '@/constants/permissions';
import { useAuth } from '@/contexts/AuthContext';
import { useRoleGuard } from '@/hooks/useRoleGuard';

export default function SupportTab() {
  const { hmore } = useAuth();
  const guard = useRoleGuard(TAB_ROLES.support);
  if (guard) return guard;
  if (!hmore) {
    return (
      <EmptyState
        title="Organisation sign-in"
        message="Support plans are available after you sign in with your organisation account."
        icon="people-outline"
      />
    );
  }
  return <TenantSupport />;
}
