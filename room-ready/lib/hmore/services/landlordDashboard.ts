import { hmoreFetch } from '@/lib/hmore/client';

/** GET /landlord-enterprise/dashboard. Rent figures are record counts, not a currency total. */
export interface LandlordEnterpriseDashboard {
  total_properties: number;
  total_rooms: number;
  occupied_rooms: number;
  vacant_rooms: number;
  active_tenancies: number;
  rent: { due: number; outstanding: number; recorded_paid: number; total: number };
  inspections: { upcoming: number; overdue: number; completed: number };
  repairs: { open: number; completed: number; pending_maintenance: number };
  properties: { id: string; name: string; city: string; postcode: string }[];
}

export function getLandlordEnterpriseDashboard(): Promise<LandlordEnterpriseDashboard> {
  return hmoreFetch<LandlordEnterpriseDashboard>('/landlord-enterprise/dashboard', { method: 'GET' });
}
