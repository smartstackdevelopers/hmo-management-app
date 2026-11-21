import { Platform } from 'react-native';

import { resolveDevHost } from '@/lib/network';

/**
 * FastAPI base for the tenant app, including the `/api/v1` prefix.
 * Native: `EXPO_PUBLIC_HMORE_API_URL` (LAN IP for phone) wins.
 * Web/laptop browser: always localhost — browsers often block localhost→LAN fetches.
 */
export function resolveHmoreApiBase(options?: {
  envUrl?: string | null;
  devHost?: string;
  platform?: typeof Platform.OS;
}): string {
  const platform = options?.platform ?? Platform.OS;
  if (platform === 'web') {
    // Same-origin via Metro proxy (metro.config.js → FastAPI :8000). Avoids browser
    // blocking cross-origin calls from :8081 to :8000.
    if (typeof window !== 'undefined' && window.location?.origin) {
      return `${window.location.origin}/api/v1`;
    }
    return '/api/v1';
  }
  const fromEnv =
    options && 'envUrl' in options ? options.envUrl : process.env.EXPO_PUBLIC_HMORE_API_URL;
  const trimmed = fromEnv?.trim();
  if (trimmed) return trimmed.replace(/\/+$/, '');
  const host = options?.devHost ?? resolveDevHost();
  return `http://${host}:8000/api/v1`;
}

export const HMORE_API_BASE_URL = resolveHmoreApiBase();
