import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type EmploymentSummary = {
  tenant_id: string;
  assessment_status: string | null;
  completion_percent: number | null;
  cv_count: number;
  application_count: number;
  open_goals: number;
  skill_names: string[];
  staff_support_notes?: string | null;
  career_goals?: string[];
};

export async function fetchEmploymentSummary(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  tenantId: string;
}): Promise<EmploymentSummary> {
  const response = await fetch(
    `${API_BASE}/api/v1/employment/staff/tenants/${options.tenantId}/summary`,
    {
      headers: {
        Authorization: `Bearer ${options.accessToken}`,
        ...organisationRequestHeaders({
          organisationId: options.organisationId,
          role: options.role,
        }),
      },
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw new Error((await response.text()) || `Request failed (${response.status})`);
  }
  return (await response.json()) as EmploymentSummary;
}

export async function saveEmploymentSupportNotes(options: {
  accessToken: string;
  tenantId: string;
  organisationId: string;
  role?: string | null;
  notes: string;
}): Promise<EmploymentSummary> {
  const response = await fetch(
    `${API_BASE}/api/v1/employment/staff/tenants/${options.tenantId}/support-notes`,
    {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${options.accessToken}`,
        "Content-Type": "application/json",
        ...organisationRequestHeaders({
          organisationId: options.organisationId,
          role: options.role,
        }),
      },
      body: JSON.stringify({ notes: options.notes }),
      cache: "no-store",
    },
  );
  if (!response.ok) {
    throw new Error((await response.text()) || `Request failed (${response.status})`);
  }
  return (await response.json()) as EmploymentSummary;
}

export type JobMatchProgress = {
  tenant_id: string;
  saved_jobs: number;
  match_count: number;
  top_scores: number[];
  career_goals: string[];
  preferred_categories: string[];
};

export async function fetchJobMatchProgress(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  tenantId: string;
}): Promise<JobMatchProgress | null> {
  const response = await fetch(
    `${API_BASE}/api/v1/job-matching/staff/tenants/${options.tenantId}/progress`,
    {
      headers: {
        Authorization: `Bearer ${options.accessToken}`,
        ...organisationRequestHeaders({
          organisationId: options.organisationId,
          role: options.role,
        }),
      },
      cache: "no-store",
    },
  );
  if (response.status === 404 || response.status === 403) return null;
  if (!response.ok) {
    throw new Error((await response.text()) || `Request failed (${response.status})`);
  }
  return (await response.json()) as JobMatchProgress;
}
