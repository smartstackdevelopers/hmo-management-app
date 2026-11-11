import { hmoreFetch } from '@/lib/hmore/client';

export async function getWellbeingDisclaimer() {
  return hmoreFetch<{ disclaimer: string }>('/wellbeing/disclaimer', { method: 'GET' });
}

export async function getWellbeingDashboard() {
  return hmoreFetch<Record<string, unknown>>('/wellbeing/dashboard', { method: 'GET' });
}

export async function upsertCheckin(body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>('/wellbeing/checkins', { method: 'PUT', body });
}

export async function listCheckins(query?: { days?: number; page?: number; page_size?: number }) {
  return hmoreFetch<{ items: Array<Record<string, unknown>>; disclaimer: string }>(
    '/wellbeing/checkins',
    { method: 'GET', query },
  );
}

export async function deleteCheckin(checkinId: string) {
  return hmoreFetch<{ status: string }>(`/wellbeing/checkins/${checkinId}`, { method: 'DELETE' });
}

export async function listRoutines(query?: { day?: string }) {
  return hmoreFetch<{ items: Array<Record<string, unknown>>; progress: Record<string, number>; note?: string }>(
    '/wellbeing/routines',
    { method: 'GET', query },
  );
}

export async function createRoutine(body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>('/wellbeing/routines', { method: 'POST', body });
}

export async function updateRoutine(routineId: string, body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>(`/wellbeing/routines/${routineId}`, {
    method: 'PUT',
    body,
  });
}

export async function deleteRoutine(routineId: string) {
  return hmoreFetch<{ status: string }>(`/wellbeing/routines/${routineId}`, { method: 'DELETE' });
}

export async function setRoutineStatus(routineId: string, body: Record<string, unknown>) {
  return hmoreFetch<Record<string, unknown>>(`/wellbeing/routines/${routineId}/status`, {
    method: 'POST',
    body,
  });
}

export async function listResources(query?: { kind?: string; category?: string }) {
  return hmoreFetch<{ items: Array<Record<string, unknown>>; disclaimer: string }>(
    '/wellbeing/resources',
    { method: 'GET', query },
  );
}

export async function saveResource(resourceId: string) {
  return hmoreFetch<{ status: string }>(`/wellbeing/resources/${resourceId}/save`, { method: 'POST' });
}

export async function completeResource(resourceId: string, status: 'completed' | 'stopped') {
  return hmoreFetch<{ status: string }>(`/wellbeing/resources/${resourceId}/complete`, {
    method: 'POST',
    body: { status },
  });
}

export async function listDirectory(query?: { category?: string }) {
  return hmoreFetch<{ items: Array<Record<string, unknown>>; disclaimer: string }>(
    '/wellbeing/directory',
    { method: 'GET', query },
  );
}

export async function listNavigatorCategories() {
  return hmoreFetch<{ items: Array<Record<string, unknown>>; disclaimer: string }>(
    '/wellbeing/navigator/categories',
    { method: 'GET' },
  );
}

export async function getNavigator(categoryId: string) {
  return hmoreFetch<Record<string, unknown>>(`/wellbeing/navigator/${categoryId}`, { method: 'GET' });
}
