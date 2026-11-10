import { OfflineDraftsScreen } from '@/components/offline/OfflineDraftsScreen';
import { useAuth } from '@/contexts/AuthContext';

export default function OfflineDraftsRoute() {
  const { hmore } = useAuth();
  if (!hmore) return null;
  return <OfflineDraftsScreen />;
}
