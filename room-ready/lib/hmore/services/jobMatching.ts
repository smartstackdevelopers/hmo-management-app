import { hmoreFetch } from '@/lib/hmore/client';

export async function getJobMatchProfile() {
  return hmoreFetch<Record<string, unknown>>('/job-matching/profile', { method: 'GET' });
}

export async function getJobMatchPreferences() {
  return hmoreFetch<Record<string, unknown>>('/job-matching/preferences', { method: 'GET' });
}

export async function updateJobMatchPreferences(body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>('/job-matching/preferences', { method: 'PUT', body });
}

export async function searchMatchedJobs(query?: Record<string, string | number | boolean | undefined>) {
  return hmoreFetch<{
    items: Array<Record<string, unknown>>;
    total: number;
    sources_used: string[];
    sources_unavailable: Array<Record<string, unknown>>;
    disclaimer: string;
  }>('/job-matching/jobs/search', { method: 'GET', query });
}

export async function recommendedJobs() {
  return hmoreFetch<{ items: Array<Record<string, unknown>>; disclaimer: string }>(
    '/job-matching/jobs/recommended',
    { method: 'GET' },
  );
}

export async function getMatchedJob(jobId: string) {
  return hmoreFetch<Record<string, unknown>>(`/job-matching/jobs/${jobId}`, { method: 'GET' });
}

export async function saveMatchedJob(jobId: string) {
  return hmoreFetch<{ status: string }>(`/job-matching/saved-jobs/${jobId}`, { method: 'POST' });
}

export async function listSavedMatchedJobs() {
  return hmoreFetch<{ items: Array<Record<string, unknown>> }>('/job-matching/saved-jobs', { method: 'GET' });
}

export async function listTrainingRecommendations() {
  return hmoreFetch<{ items: Array<Record<string, unknown>>; disclaimer?: string }>(
    '/job-matching/training',
    { method: 'GET' },
  );
}

export async function addMatchedJobToTracker(body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>('/job-matching/tracker', { method: 'POST', body });
}

export async function explainJobMatch(body: { job_id: string; question?: string }) {
  return hmoreFetch<Record<string, unknown>>('/job-matching/explain', { method: 'POST', body });
}

export async function listJobSources() {
  return hmoreFetch<{ sources: Array<Record<string, unknown>> }>('/job-matching/sources', { method: 'GET' });
}
