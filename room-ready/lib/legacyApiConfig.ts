/** Legacy Room Ready password API — explicit opt-in only (no port 3001 default). */

export class LegacyApiConfigurationError extends Error {
  constructor() {
    super(
      'EXPO_PUBLIC_API_URL is not set. HMore Auth0 flows use EXPO_PUBLIC_HMORE_API_URL (FastAPI on port 8000). ' +
        'Set EXPO_PUBLIC_API_URL only when intentionally using the legacy Room Ready password API.',
    );
    this.name = 'LegacyApiConfigurationError';
  }
}

export function resolveLegacyApiBaseUrl(): string {
  const raw = process.env.EXPO_PUBLIC_API_URL?.trim();
  if (!raw) {
    throw new LegacyApiConfigurationError();
  }
  return raw.replace(/\/+$/, '');
}