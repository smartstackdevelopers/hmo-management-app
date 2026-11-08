import { hmoreFetch } from '@/lib/hmore/client';
import type { HousingApplication, Page } from '@/lib/hmore/types';

export function listHousingApplications(): Promise<Page<HousingApplication>> {
  return hmoreFetch<Page<HousingApplication>>('/housing-applications', {
    method: 'GET',
    query: { page: 1, page_size: 50 },
  });
}

export function getHousingApplication(id: string): Promise<HousingApplication> {
  return hmoreFetch<HousingApplication>(`/housing-applications/${id}`, { method: 'GET' });
}
