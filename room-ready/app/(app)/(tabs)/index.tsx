import DashboardScreen from '@/components/dashboard/DashboardScreen';
import { StaffHome } from '@/components/staff/StaffHome';
import { StaffMobileLater } from '@/components/tenant/StaffMobileLater';
import { TenantHome } from '@/components/tenant/TenantHome';
import { staffShellActive } from '@/constants/navigation';
import { useAuth } from '@/contexts/AuthContext';

export default function HomeTab() {
  const { hmore, user } = useAuth();
  if (hmore && user?.role === 'tenant') return <TenantHome />;
  if (staffShellActive(user?.role, !!hmore)) return <StaffHome />;
  if (hmore) return <StaffMobileLater />;
  return <DashboardScreen />;
}
