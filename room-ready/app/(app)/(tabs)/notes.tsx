import { DailyNoteEditor } from '@/components/staff/DailyNoteEditor';
import { useAuth } from '@/contexts/AuthContext';
import { isSupportShellRole } from '@/lib/hmore/roles';

export default function NotesScreen() {
  const { hmore, user } = useAuth();
  if (!hmore || !isSupportShellRole(user?.role)) return null;
  return <DailyNoteEditor />;
}
