import { getStoredAccessToken } from '@/lib/hmoreAuth0';

import { HMORE_API_BASE_URL } from './config';
import { getRequestContext, type HmoreRequestContext } from './requestContext';

export class HmoreApiError extends Error {
  readonly status: number;
  readonly detail: string;

  constructor(status: number, detail: string) {
    super(detail);
    this.name = 'HmoreApiError';
    this.status = status;
    this.detail = detail;
  }
}

export type HmoreRequestInit = {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | boolean | null | undefined>;
  signal?: AbortSignal;
};

export type HmoreClientDeps = {
  getAccessToken: () => Promise<string | null>;
  getContext: () => HmoreRequestContext;
  fetchImpl: typeof fetch;
  baseUrl: string;
};

const defaultDeps: HmoreClientDeps = {
  getAccessToken: getStoredAccessToken,
  getContext: getRequestContext,
  fetchImpl: fetch,
  baseUrl: HMORE_API_BASE_URL,
};

function buildUrl(baseUrl: string, path: string, query?: HmoreRequestInit['query']): string {
  const base = baseUrl.replace(/\/+$/, '');
  const suffix = path.startsWith('/') ? path : `/${path}`;
  const url = new URL(`${base}${suffix}`);
  if (query) {
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === '') continue;
      url.searchParams.set(key, String(value));
    }
  }
  return url.toString();
}

function messageFromDetail(detail: unknown): string | null {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) {
          const msg = (item as { msg?: unknown }).msg;
          return typeof msg === 'string' ? msg : null;
        }
        return null;
      })
      .filter((item): item is string => !!item);
    return messages.length > 0 ? messages.join('. ') : null;
  }
  if (detail && typeof detail === 'object') {
    const obj = detail as { message?: unknown; detail?: unknown };
    if (typeof obj.message === 'string' && obj.message.trim()) return obj.message;
    if (typeof obj.detail === 'string' && obj.detail.trim()) return obj.detail;
  }
  return null;
}

function readDetail(data: unknown, status: number): string {
  if (data && typeof data === 'object') {
    const record = data as { detail?: unknown; error?: unknown; message?: unknown };
    const fromDetail = messageFromDetail(record.detail);
    if (fromDetail) return fromDetail;
    if (typeof record.message === 'string' && record.message.trim()) return record.message;
    if (typeof record.error === 'string' && record.error.trim() && record.error !== 'ai_budget_exceeded') {
      return record.error;
    }
  }
  return `Request failed (${status})`;
}

export async function hmoreRequest<T>(
  path: string,
  init: HmoreRequestInit = {},
  deps: HmoreClientDeps = defaultDeps,
): Promise<T> {
  const response = await hmoreRequestResponse(path, init, deps);
  if (response.status === 204) return undefined as T;
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new HmoreApiError(response.status, readDetail(data, response.status));
  }
  return data as T;
}

export async function hmoreRequestResponse(
  path: string,
  init: HmoreRequestInit = {},
  deps: HmoreClientDeps = defaultDeps,
): Promise<Response> {
  const token = await deps.getAccessToken();
  const context = deps.getContext();
  const headers: Record<string, string> = {};

  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  if (context.organisationId) {
    headers['X-Organisation-Id'] = context.organisationId;
  }
  if (context.role) {
    headers['X-HMore-Role'] = context.role;
  }

  let body: BodyInit | undefined;
  if (init.formData) {
    body = init.formData;
  } else if (init.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(init.body);
  }

  let response: Response;
  try {
    response = await deps.fetchImpl(buildUrl(deps.baseUrl, path, init.query), {
      method: init.method ?? (body ? 'POST' : 'GET'),
      headers,
      body,
      signal: init.signal,
    });
  } catch {
    throw new HmoreApiError(0, 'Could not reach HMore. Check your connection and API address.');
  }

  if (!response.ok && init.formData) {
    const data = await response.json().catch(() => ({}));
    throw new HmoreApiError(response.status, readDetail(data, response.status));
  }
  return response;
}

export function hmoreFetch<T>(path: string, init?: HmoreRequestInit): Promise<T> {
  return hmoreRequest<T>(path, init);
}

export function hmoreErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (error instanceof HmoreApiError) return error.detail || fallback;
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}
