import DashboardScreen from '@/components/dashboard/DashboardScreen';
import { StaffMobileLater } from '@/components/tenant/StaffMobileLater';
import { TenantHome } from '@/components/tenant/TenantHome';
import { useAuth } from '@/contexts/AuthContext';

export default function HomeTab() {
  const { hmore, user } = useAuth();
  if (hmore && user?.role === 'tenant') return <TenantHome />;
  if (hmore) return <StaffMobileLater />;
  return <DashboardScreen />;
}
