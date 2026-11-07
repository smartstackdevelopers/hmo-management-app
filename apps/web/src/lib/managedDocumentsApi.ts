/**
 * F2.11 managed documents API client (organisation-scoped).
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type DocSummary = Record<string, unknown>;

export type Paged<T> = {
  items: T[];
  page: number;
  page_size: number;
  total: number;
};

export async function documentsFetch<T>(
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
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function fetchDocumentsDashboard(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<Record<string, unknown>> {
  return documentsFetch<Record<string, unknown>>("/api/v1/documents/dashboard", options);
}

export async function listDocumentCategories(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<Array<{ id: string; code: string; title: string }>> {
  const rows = await documentsFetch<DocSummary[]>("/api/v1/documents/categories", options);
  return rows.map((c) => ({
    id: String(c.id),
    code: String(c.code),
    title: String(c.title),
  }));
}

export async function seedDocumentCategories(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<{ created: number }> {
  return documentsFetch<{ created: number }>("/api/v1/documents/categories/seed-defaults", {
    ...options,
    method: "POST",
  });
}

export async function listDocuments(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  page?: number;
  pageSize?: number;
  q?: string;
}): Promise<Paged<DocSummary>> {
  const q = new URLSearchParams();
  q.set("page", String(options.page ?? 1));
  q.set("page_size", String(options.pageSize ?? 20));
  if (options.q) {
    q.set("q", options.q);
  }
  return documentsFetch(`/api/v1/documents?${q.toString()}`, options);
}

export async function listExpiringDocuments(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  page?: number;
  pageSize?: number;
}): Promise<Paged<DocSummary>> {
  const q = new URLSearchParams();
  q.set("page", String(options.page ?? 1));
  q.set("page_size", String(options.pageSize ?? 20));
  return documentsFetch(`/api/v1/documents/expiring?${q.toString()}`, options);
}

export async function listExpiredDocuments(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  page?: number;
  pageSize?: number;
}): Promise<Paged<DocSummary>> {
  const q = new URLSearchParams();
  q.set("page", String(options.page ?? 1));
  q.set("page_size", String(options.pageSize ?? 20));
  return documentsFetch(`/api/v1/documents/expired?${q.toString()}`, options);
}

export async function listRetentionPendingDocuments(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  page?: number;
  pageSize?: number;
}): Promise<Paged<DocSummary>> {
  const q = new URLSearchParams();
  q.set("page", String(options.page ?? 1));
  q.set("page_size", String(options.pageSize ?? 20));
  return documentsFetch(`/api/v1/documents/retention/pending-review?${q.toString()}`, options);
}

export async function getDocument(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  documentId: string;
}): Promise<DocSummary> {
  return documentsFetch(`/api/v1/documents/${options.documentId}`, options);
}

export async function listDocumentVersions(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  documentId: string;
}): Promise<unknown[]> {
  return documentsFetch(`/api/v1/documents/${options.documentId}/versions`, options);
}

export async function getSignatureRequest(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  signatureId: string;
}): Promise<DocSummary> {
  return documentsFetch(`/api/v1/documents/signature-requests/${options.signatureId}`, options);
}

export async function listMyAccessRequests(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<unknown[]> {
  return documentsFetch("/api/v1/documents/me/access-requests", options);
}

export async function listPendingAccessRequests(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<unknown[]> {
  return documentsFetch("/api/v1/documents/access-requests/pending-review", options);
}

export async function listPendingSignatures(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<unknown[]> {
  return documentsFetch("/api/v1/documents/signature-requests/pending", options);
}

export async function listMyPendingSignatures(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}): Promise<unknown[]> {
  return documentsFetch("/api/v1/documents/me/signature-requests", options);
}

export async function completeSignatureRequest(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  signatureId: string;
  body: { consent_text: string; acknowledgement: string };
}): Promise<unknown> {
  const { signatureId, body, ...rest } = options;
  return documentsFetch(`/api/v1/documents/signature-requests/${signatureId}/complete`, {
    ...rest,
    method: "POST",
    body,
  });
}

export async function declineSignatureRequest(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  signatureId: string;
  body?: { reason?: string | null };
}): Promise<unknown> {
  const { signatureId, body, ...rest } = options;
  return documentsFetch(`/api/v1/documents/signature-requests/${signatureId}/decline`, {
    ...rest,
    method: "POST",
    body: body ?? {},
  });
}

export async function createAccessRequest(options: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  documentId: string;
  body: { reason: string };
}): Promise<unknown> {
  const { documentId, body, ...rest } = options;
  return documentsFetch(`/api/v1/documents/${documentId}/access-requests`, {
    ...rest,
    method: "POST",
    body,
  });
}

export function managedDocumentContentUrl(documentId: string): string {
  return `${API_BASE}/api/v1/documents/${documentId}/content`;
}
