import { getStoredAccessToken } from '@/lib/hmoreAuth0';

import { resolveHmoreApiBase } from './config';
import { getRequestContext, type HmoreRequestContext } from './requestContext';
import { readDeviceSessionId } from './security/deviceSessionStore';
import { handleRemoteDeviceSessionRevoked } from './security/deviceSessionRevoke';

export class HmoreApiError extends Error {
  readonly status: number;
  readonly detail: string;
  readonly data: unknown;

  constructor(status: number, detail: string, data?: unknown) {
    super(detail);
    this.name = 'HmoreApiError';
    this.status = status;
    this.detail = detail;
    this.data = data;
  }
}

export type HmoreRequestInit = {
  method?: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
  body?: unknown;
  formData?: FormData;
  query?: Record<string, string | number | boolean | null | undefined>;
  signal?: AbortSignal;
  headers?: Record<string, string>;
  idempotencyKey?: string;
};

export type HmoreClientDeps = {
  getAccessToken: () => Promise<string | null>;
  getContext: () => HmoreRequestContext;
  fetchImpl: typeof fetch;
  baseUrl: string;
  getDeviceSessionId?: () => Promise<string | null>;
  onDeviceSessionRevoked?: () => Promise<void>;
};

const defaultDeps: HmoreClientDeps = {
  getAccessToken: getStoredAccessToken,
  getContext: getRequestContext,
  // Bind fetch — unbound `fetch` throws "Illegal invocation" in browsers (Expo web).
  fetchImpl: ((input: RequestInfo | URL, init?: RequestInit) =>
    globalThis.fetch(input, init)) as typeof fetch,
  // Resolve per request so web always uses Metro proxy origin.
  get baseUrl() {
    return resolveHmoreApiBase();
  },
};

function buildUrl(baseUrl: string, path: string, query?: HmoreRequestInit['query']): string {
  const base = baseUrl.replace(/\/+$/, '');
  const suffix = path.startsWith('/') ? path : `/${path}`;
  let url = `${base}${suffix}`;
  if (query) {
    const parts: string[] = [];
    for (const [key, value] of Object.entries(query)) {
      if (value === undefined || value === null || value === '') continue;
      parts.push(`${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
    }
    if (parts.length > 0) url += `?${parts.join('&')}`;
  }
  return url;
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
    throw new HmoreApiError(response.status, readDetail(data, response.status), data);
  }
  return data as T;
}

export async function hmoreRequestResponse(
  path: string,
  init: HmoreRequestInit = {},
  deps: HmoreClientDeps = defaultDeps,
): Promise<Response> {
  const context = deps.getContext();
  const headers: Record<string, string> = {};

  if (context.organisationId) {
    headers['X-Organisation-Id'] = context.organisationId;
  }
  if (context.role) {
    headers['X-HMore-Role'] = context.role;
  }
  if (init.idempotencyKey) {
    headers['Idempotency-Key'] = init.idempotencyKey;
  }
  const sessionId = await (deps.getDeviceSessionId ?? readDeviceSessionId)();
  if (sessionId) {
    headers['X-Device-Session-Id'] = sessionId;
  }
  if (init.headers) {
    Object.assign(headers, init.headers);
  }

  // Prefer an explicit Authorization header from the caller (e.g. session bootstrap).
  // Otherwise load the stored access token — never call protected APIs anonymously.
  if (!headers.Authorization) {
    const token = await deps.getAccessToken();
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
  }
  if (!headers.Authorization) {
    throw new HmoreApiError(401, 'Please sign in again');
  }

  let body: BodyInit | undefined;
  if (init.formData) {
    body = init.formData;
  } else if (init.body !== undefined) {
    headers['Content-Type'] = 'application/json';
    body = JSON.stringify(init.body);
  }

  const requestUrl = buildUrl(deps.baseUrl, path, init.query);
  let response: Response;
  try {
    response = await deps.fetchImpl(requestUrl, {
      method: init.method ?? (body ? 'POST' : 'GET'),
      headers,
      body,
      signal: init.signal,
    });
  } catch (err) {
    const why = err instanceof Error ? err.message : 'network error';
    throw new HmoreApiError(0, `Could not reach HMore at ${requestUrl} (${why}).`);
  }

  if (!response.ok && init.formData) {
    await noteDeviceSessionRevoked(response, deps);
    const data = await response.json().catch(() => ({}));
    throw new HmoreApiError(response.status, readDetail(data, response.status), data);
  }
  await noteDeviceSessionRevoked(response, deps);
  return response;
}

async function noteDeviceSessionRevoked(response: Response, deps: HmoreClientDeps): Promise<void> {
  if (response.status !== 401 || typeof response.clone !== 'function') return;
  const data = await response.clone().json().catch(() => null);
  const detail = data && typeof data === 'object' ? (data as { detail?: unknown }).detail : undefined;
  if (detail !== 'device_session_revoked') return;
  const handler = deps.onDeviceSessionRevoked ?? handleRemoteDeviceSessionRevoked;
  await handler();
}

export function hmoreFetch<T>(path: string, init?: HmoreRequestInit): Promise<T> {
  return hmoreRequest<T>(path, init);
}

export function conflictUpdatedAt(error: unknown): string | undefined {
  if (!(error instanceof HmoreApiError) || error.status !== 409 || !error.data || typeof error.data !== 'object') return undefined;
  const detail = (error.data as { detail?: unknown }).detail;
  if (!detail || typeof detail !== 'object') return undefined;
  const stamp = (detail as { updated_at?: unknown }).updated_at;
  return typeof stamp === 'string' && stamp ? stamp : undefined;
}

export function hmoreErrorMessage(error: unknown, fallback = 'Something went wrong'): string {
  if (error instanceof HmoreApiError) return error.detail || fallback;
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}
