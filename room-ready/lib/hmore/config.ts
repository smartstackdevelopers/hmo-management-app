import { resolveDevHost } from '@/lib/config';

/**
 * FastAPI base for the tenant app, including the `/api/v1` prefix.
 * `EXPO_PUBLIC_HMORE_API_URL` wins. Otherwise the dev machine on port 8000.
 */
export function resolveHmoreApiBase(options?: {
  envUrl?: string | null;
  devHost?: string;
}): string {
  const fromEnv =
    options && 'envUrl' in options ? options.envUrl : process.env.EXPO_PUBLIC_HMORE_API_URL;
  const trimmed = fromEnv?.trim();
  if (trimmed) return trimmed.replace(/\/+$/, '');
  const host = options?.devHost ?? resolveDevHost();
  return `http://${host}:8000/api/v1`;
}

export const HMORE_API_BASE_URL = resolveHmoreApiBase();
