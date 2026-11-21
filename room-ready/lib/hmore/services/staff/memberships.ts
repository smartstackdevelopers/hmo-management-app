import { hmoreFetch } from '@/lib/hmore/client';

export interface OrganisationMembershipRow {
  id: string;
  user_id: string;
  role: string;
  status: string;
}

export function listOrganisationMemberships(organisationId: string): Promise<{
  organisation_id: string;
  memberships: OrganisationMembershipRow[];
}> {
  return hmoreFetch(`/organisations/${organisationId}/memberships`, { method: 'GET' });
}
