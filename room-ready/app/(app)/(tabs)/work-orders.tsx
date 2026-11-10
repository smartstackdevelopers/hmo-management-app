import { WorkOrderList } from '@/components/staff/WorkOrderList';
import { useAuth } from '@/contexts/AuthContext';

export default function WorkOrdersScreen() {
  const { hmore, user } = useAuth();
  if (!hmore || user?.role !== 'contractor') return null;
  return <WorkOrderList />;
}
