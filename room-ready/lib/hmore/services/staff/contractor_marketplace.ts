import { hmoreFetch } from '@/lib/hmore/client';

export function getContractorWorkspaceJobs(): Promise<Record<string, unknown>[]> {
  return hmoreFetch<Record<string, unknown>[]>('/contractor-marketplace/workspace/jobs', { method: 'GET' });
}

export function searchApprovedContractors(): Promise<Record<string, unknown>[]> {
  return hmoreFetch<Record<string, unknown>[]>('/contractor-marketplace/marketplace', { method: 'GET' });
}
