import { hmoreFetch } from '@/lib/hmore/client';

export function getTenantEngagementDashboard(tenantUserId: string): Promise<Record<string, unknown>> {
  return hmoreFetch<Record<string, unknown>>(
    `/tenant-engagement/tenant/dashboard?tenant_user_id=${encodeURIComponent(tenantUserId)}`,
    { method: 'GET' },
  );
}
