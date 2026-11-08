import { Phase5Notice } from '@/components/tenant/Phase5Notice';
import { jobsAndTrainingStatus } from '@/lib/hmore/services/jobs';

export default function JobsScreen() {
  return <Phase5Notice result={jobsAndTrainingStatus()} />;
}
