import { hmoreFetch } from '@/lib/hmore/client';

export async function getSkillCategories() {
  return hmoreFetch<{ categories: string[]; levels: string[] }>('/employment/skill-categories', {
    method: 'GET',
  });
}

export async function getAssessment() {
  return hmoreFetch<Record<string, unknown>>('/employment/assessment', { method: 'GET' });
}

export async function updateAssessment(body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>('/employment/assessment', {
    method: 'PUT',
    body,
  });
}

export async function listCvs() {
  return hmoreFetch<{ items: Array<Record<string, unknown>> }>('/employment/cvs', { method: 'GET' });
}

export async function createCv(body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>('/employment/cvs', { method: 'POST', body });
}

export async function getCv(cvId: string) {
  return hmoreFetch<Record<string, unknown>>(`/employment/cvs/${cvId}`, { method: 'GET' });
}

export async function updateCv(cvId: string, body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>(`/employment/cvs/${cvId}`, { method: 'PATCH', body });
}

export async function duplicateCv(cvId: string) {
  return hmoreFetch<Record<string, unknown>>(`/employment/cvs/${cvId}/duplicate`, { method: 'POST' });
}

export async function deleteCv(cvId: string) {
  return hmoreFetch<{ status: string }>(`/employment/cvs/${cvId}`, { method: 'DELETE' });
}

export async function generateCvPdf(cvId: string) {
  return hmoreFetch<Record<string, unknown>>(`/employment/cvs/${cvId}/pdf`, { method: 'POST' });
}

export async function assistCvWording(body: { field: string; original_text: string }) {
  return hmoreFetch<Record<string, unknown>>('/employment/cvs/assist', { method: 'POST', body });
}

export async function getApplicationDashboard() {
  return hmoreFetch<Record<string, unknown>>('/employment/applications/dashboard', { method: 'GET' });
}

export async function listApplications(query?: { status?: string; q?: string }) {
  return hmoreFetch<{ items: Array<Record<string, unknown>>; total: number }>('/employment/applications', {
    method: 'GET',
    query,
  });
}

export async function createApplication(body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>('/employment/applications', { method: 'POST', body });
}

export async function updateApplication(id: string, body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>(`/employment/applications/${id}`, { method: 'PATCH', body });
}

export async function getRoadmap() {
  return hmoreFetch<Record<string, unknown>>('/employment/roadmap', { method: 'GET' });
}

export async function createCareerGoal(body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>('/employment/career-goals', { method: 'POST', body });
}

export async function getInterviewPrep() {
  return hmoreFetch<Record<string, unknown>>('/employment/interview-prep', { method: 'GET' });
}

export async function saveInterviewPrep(body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>('/employment/interview-prep', { method: 'POST', body });
}
