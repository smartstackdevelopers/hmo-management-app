import { hmoreFetch } from '@/lib/hmore/client';
import { surveySummariesFromResponse, type OccupancySurveySummary } from '@/lib/hmore/staff/occupancyView';

export async function listOccupancySurveys(): Promise<OccupancySurveySummary[]> {
  const data = await hmoreFetch<unknown>('/occupancy-surveys', {
    method: 'GET',
    query: { page: 1, page_size: 50 },
  });
  return surveySummariesFromResponse(data);
}
