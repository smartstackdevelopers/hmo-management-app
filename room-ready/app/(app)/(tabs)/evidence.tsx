import { PhotoEvidence } from '@/components/staff/PhotoEvidence';
import { useAuth } from '@/contexts/AuthContext';

export default function EvidenceScreen() {
  const { hmore, user } = useAuth();
  if (!hmore || user?.role !== 'contractor') return null;
  return <PhotoEvidence />;
}
