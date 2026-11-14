import { organisationRequestHeaders } from "@/lib/organisation";
import type { GovAuth } from "@/lib/platformGovernanceApi";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type CreatedOrganisation = {
  id: string;
  name: string;
  slug: string;
};

export async function createOrganisation(
  auth: GovAuth,
  body: { name: string; slug: string },
): Promise<CreatedOrganisation> {
  const response = await fetch(`${API_BASE}/api/v1/organisations`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${auth.accessToken}`,
      "Content-Type": "application/json",
      ...organisationRequestHeaders({
        organisationId: auth.organisationId,
        role: auth.role ?? "super_admin",
      }),
    },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Create failed (${response.status})`);
  }
  return response.json() as Promise<CreatedOrganisation>;
}