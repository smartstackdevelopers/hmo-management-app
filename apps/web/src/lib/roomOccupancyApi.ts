import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type OccupancyAuth = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

async function occFetch<T>(path: string, options: OccupancyAuth, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      "Content-Type": "application/json",
      ...organisationRequestHeaders({
        organisationId: options.organisationId,
        role: options.role,
      }),
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });
  if (!response.ok) throw new Error(await response.text());
  return response.json() as Promise<T>;
}

export function fetchOccupancyDashboard(options: OccupancyAuth) {
  return occFetch<Record<string, unknown>>("/api/v1/room-occupancy/dashboard", options);
}

export function fetchOccupancyRooms(
  options: OccupancyAuth & { propertyId?: string; floor?: string; status?: string },
) {
  const params = new URLSearchParams();
  if (options.propertyId) params.set("property_id", options.propertyId);
  if (options.floor) params.set("floor", options.floor);
  if (options.status) params.set("occupancy_status", options.status);
  const q = params.toString();
  return occFetch<{ items: Record<string, unknown>[] }>(
    `/api/v1/room-occupancy/rooms${q ? `?${q}` : ""}`,
    options,
  );
}

export function updateApprovalGate(options: OccupancyAuth, body: Record<string, unknown>) {
  return occFetch<Record<string, unknown>>("/api/v1/room-occupancy/approval-gate", options, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export function fetchOccupancyAlerts(options: OccupancyAuth) {
  return occFetch<{ items: Record<string, unknown>[] }>("/api/v1/room-occupancy/alerts?status=active", options);
}

export function fetchOccupancyUsage(options: OccupancyAuth, period = "daily") {
  return occFetch<Record<string, unknown>>(
    `/api/v1/room-occupancy/reports/usage?period=${period}`,
    options,
  );
}

export function correctOccupancyCount(
  options: OccupancyAuth,
  roomId: string,
  body: { corrected_count: number; reason: string },
) {
  return occFetch<Record<string, unknown>>(`/api/v1/room-occupancy/rooms/${roomId}/correct`, options, {
    method: "POST",
    body: JSON.stringify(body),
  });
}
