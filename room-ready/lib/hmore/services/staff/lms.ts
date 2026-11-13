import { hmoreFetch } from '@/lib/hmore/client';

export function getLmsDashboard(): Promise<Record<string, unknown>> {
  return hmoreFetch<Record<string, unknown>>('/lms/learn/dashboard', { method: 'GET' });
}

export function listLmsCourses(): Promise<Record<string, unknown>[]> {
  return hmoreFetch<Record<string, unknown>[]>('/lms/learn/courses', { method: 'GET' });
}
