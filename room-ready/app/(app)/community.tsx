import { Phase5Notice } from '@/components/tenant/Phase5Notice';
import { communityServicesStatus } from '@/lib/hmore/services/community';

export default function CommunityScreen() {
  return <Phase5Notice result={communityServicesStatus()} />;
}
