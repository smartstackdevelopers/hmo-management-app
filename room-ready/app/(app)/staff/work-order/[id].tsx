import { WorkOrderDetail } from '@/components/staff/WorkOrderDetail';
import { useAuth } from '@/contexts/AuthContext';

export default function WorkOrderScreen() {
  const { hmore, user } = useAuth();
  if (!hmore || user?.role !== 'contractor') return null;
  return <WorkOrderDetail />;
}
