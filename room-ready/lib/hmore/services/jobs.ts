import { PHASE5_PENDING, type Phase5PendingResult } from '@/lib/hmore/types';

const MESSAGE =
  'Jobs and training ideas are a Phase 5 module. This screen stays empty until that service is connected. There is no sample list.';

export function jobsAndTrainingStatus(): Phase5PendingResult {
  return { status: PHASE5_PENDING, feature: 'jobs', message: MESSAGE };
}
