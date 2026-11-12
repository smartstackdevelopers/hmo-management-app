import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function landlordFetch<T>(
  path: string,
  options: {
    accessToken: string;
    organisationId: string;
    role?: string | null;
    method?: string;
    body?: unknown;
  },
): Promise<T> {
  const response = await fetch(`${API_BASE}/api/v1/landlord-enterprise${path}`, {
    method: options.method ?? "GET",
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      "Content-Type": "application/json",
      ...organisationRequestHeaders({
        organisationId: options.organisationId,
        role: options.role,
      }),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error((await response.text()) || `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export type LandlordDashboard = {
  total_properties: number;
  total_rooms: number;
  occupied_rooms: number;
  vacant_rooms: number;
  active_tenancies: number;
  rent: { due: number; outstanding: number; recorded_paid: number; total: number };
  inspections: { upcoming: number; overdue: number; completed: number };
  repairs: { open: number; completed: number; pending_maintenance: number };
  ledger_disclaimer: string;
  properties: Array<{ id: string; name: string; city: string; postcode: string }>;
};

export function fetchLandlordDashboard(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  return landlordFetch<LandlordDashboard>("/dashboard", options);
}

export function fetchPortfolio(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  query?: Record<string, string | undefined>;
}) {
  const params = new URLSearchParams();
  Object.entries(options.query ?? {}).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const q = params.toString();
  return landlordFetch<{ items: Array<Record<string, unknown>>; total: number; vacancy_trend: Array<Record<string, unknown>> }>(
    `/portfolio${q ? `?${q}` : ""}`,
    options,
  );
}

export function fetchRentRecords(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  query?: Record<string, string | undefined>;
}) {
  const params = new URLSearchParams();
  Object.entries(options.query ?? {}).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const q = params.toString();
  return landlordFetch<{ items: Array<Record<string, unknown>>; total: number; disclaimer: string }>(
    `/rent-records${q ? `?${q}` : ""}`,
    options,
  );
}

export function createRentRecord(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}) {
  return landlordFetch<Record<string, unknown>>("/rent-records", {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export function updateRentStatus(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  rentId: string;
  body: Record<string, unknown>;
}) {
  return landlordFetch<Record<string, unknown>>(`/rent-records/${options.rentId}/status`, {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export function archiveRentRecord(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  rentId: string;
}) {
  return landlordFetch<Record<string, unknown>>(`/rent-records/${options.rentId}`, {
    ...options,
    method: "DELETE",
  });
}

export function fetchInspections(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  query?: Record<string, string | undefined>;
}) {
  const params = new URLSearchParams();
  Object.entries(options.query ?? {}).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const q = params.toString();
  return landlordFetch<{
    items: Array<Record<string, unknown>>;
    total: number;
    upcoming: number;
    overdue: number;
  }>(`/inspections${q ? `?${q}` : ""}`, options);
}

export function createInspection(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  body: Record<string, unknown>;
}) {
  return landlordFetch<Record<string, unknown>>("/inspections", {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export function updateInspection(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  inspectionId: string;
  body: Record<string, unknown>;
}) {
  return landlordFetch<Record<string, unknown>>(`/inspections/${options.inspectionId}`, {
    ...options,
    method: "PUT",
    body: options.body,
  });
}

export function fetchRepairs(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  query?: Record<string, string | undefined>;
}) {
  const params = new URLSearchParams();
  Object.entries(options.query ?? {}).forEach(([key, value]) => {
    if (value) params.set(key, value);
  });
  const q = params.toString();
  return landlordFetch<{
    items: Array<Record<string, unknown>>;
    total: number;
    open: number;
    completed: number;
    overdue: number;
  }>(`/repairs${q ? `?${q}` : ""}`, options);
}
