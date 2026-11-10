import { TaskBoard } from '@/components/staff/TaskBoard';
import { useAuth } from '@/contexts/AuthContext';
import { isSupportShellRole } from '@/lib/hmore/roles';

export default function TasksScreen() {
  const { hmore, user } = useAuth();
  if (!hmore || !isSupportShellRole(user?.role)) return null;
  return <TaskBoard />;
}
