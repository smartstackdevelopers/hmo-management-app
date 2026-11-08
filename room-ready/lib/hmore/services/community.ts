import { PHASE5_PENDING, type Phase5PendingResult } from '@/lib/hmore/types';

const MESSAGE =
  'Food banks and local services are a Phase 5 module. This screen stays empty until that service is connected. There is no sample list.';

export function communityServicesStatus(): Phase5PendingResult {
  return { status: PHASE5_PENDING, feature: 'community', message: MESSAGE };
}
