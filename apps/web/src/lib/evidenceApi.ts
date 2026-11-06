/**
 * F2.6 evidence checklist / pack API client.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

async function evidenceFetch<T>(
  path: string,
  options: {
    accessToken: string;
    organisationId: string;
    role?: string | null;
    method?: string;
    body?: unknown;
  },
): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
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

export type EvidenceStatus =
  | "pending"
  | "received"
  | "under_review"
  | "accepted"
  | "rejected"
  | "missing"
  | "not_applicable";

export type ChecklistItem = {
  id: string;
  application_id: string;
  category: string;
  title: string;
  description?: string | null;
  is_required: boolean;
  status: EvidenceStatus;
  reviewer_notes?: string | null;
  rejection_reason?: string | null;
  submitted_at?: string | null;
  reviewed_at?: string | null;
  file_ids: string[];
  sort_order: number;
};

export type Readiness = {
  application_id: string;
  ready: boolean;
  is_complete: boolean;
  required_total: number;
  required_accepted: number;
  outstanding: Array<{ id: string; title: string; status: string }>;
};

export type EvidencePack = {
  id: string;
  application_id: string;
  status: string;
  is_complete: boolean;
  outstanding_summary?: string | null;
  generated_at: string;
  file_id?: string | null;
};

export type ReviewHistory = {
  id: string;
  from_status?: string | null;
  to_status: string;
  note?: string | null;
  created_at: string;
};

export function evidenceStatusLabel(status: string): string {
  return status.replaceAll("_", " ");
}

export function isBlockingEvidenceStatus(status: string, isRequired: boolean): boolean {
  if (!isRequired) return false;
  return !["accepted", "not_applicable"].includes(status);
}

export function packReadinessWarning(readiness: Readiness | null): string | null {
  if (!readiness) return null;
  if (readiness.is_complete) return null;
  const titles = readiness.outstanding.map((o) => o.title).join(", ");
  return `Incomplete evidence — outstanding required items: ${titles || "none listed"}`;
}

export async function fetchChecklist(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  applicationId: string;
}): Promise<ChecklistItem[]> {
  return evidenceFetch(`/api/v1/housing-applications/${options.applicationId}/evidence`, options);
}

export async function seedChecklist(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  applicationId: string;
}): Promise<ChecklistItem[]> {
  return evidenceFetch(`/api/v1/housing-applications/${options.applicationId}/evidence/seed`, {
    ...options,
    method: "POST",
    body: {},
  });
}

export async function createChecklistItem(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  applicationId: string;
  body: { title: string; category?: string; is_required?: boolean; description?: string };
}): Promise<ChecklistItem> {
  return evidenceFetch(`/api/v1/housing-applications/${options.applicationId}/evidence`, {
    ...options,
    method: "POST",
    body: options.body,
  });
}

export async function updateChecklistItem(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  itemId: string;
  body: Record<string, unknown>;
}): Promise<ChecklistItem> {
  return evidenceFetch(`/api/v1/evidence-items/${options.itemId}`, {
    ...options,
    method: "PATCH",
    body: options.body,
  });
}

export async function fetchReadiness(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  applicationId: string;
}): Promise<Readiness> {
  return evidenceFetch(
    `/api/v1/housing-applications/${options.applicationId}/evidence/readiness`,
    options,
  );
}

export async function generateEvidencePack(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  applicationId: string;
  allowIncomplete?: boolean;
}): Promise<EvidencePack> {
  return evidenceFetch(`/api/v1/housing-applications/${options.applicationId}/evidence/packs`, {
    ...options,
    method: "POST",
    body: { allow_incomplete: Boolean(options.allowIncomplete) },
  });
}

export async function listEvidencePacks(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  applicationId: string;
}): Promise<EvidencePack[]> {
  return evidenceFetch(`/api/v1/housing-applications/${options.applicationId}/evidence/packs`, options);
}

export async function fetchItemHistory(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  itemId: string;
}): Promise<ReviewHistory[]> {
  return evidenceFetch(`/api/v1/evidence-items/${options.itemId}/history`, options);
}

export function evidencePackDownloadUrl(packId: string): string {
  return `${API_BASE}/api/v1/evidence-packs/${packId}/download`;
}

export async function uploadEvidenceFile(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  itemId: string;
  file: File;
}): Promise<ChecklistItem> {
  const form = new FormData();
  form.append("upload", options.file);
  const response = await fetch(`${API_BASE}/api/v1/evidence-items/${options.itemId}/upload`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${options.accessToken}`,
      ...organisationRequestHeaders({
        organisationId: options.organisationId,
        role: options.role,
      }),
    },
    body: form,
  });
  if (!response.ok) {
    throw new Error((await response.text()) || `Upload failed (${response.status})`);
  }
  return (await response.json()) as ChecklistItem;
}
