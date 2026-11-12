/**
 * F7.7 — production API URL checks (no secrets).
 * EAS production builds should set EXPO_PUBLIC_HMORE_API_URL via EAS secrets.
 */

export function validateProductionApiUrl(url: string | null | undefined): string | null {
  const trimmed = url?.trim();
  if (!trimmed) {
    return 'EXPO_PUBLIC_HMORE_API_URL is required for production store builds';
  }
  if (!/^https:\/\//i.test(trimmed)) {
    return 'Production API must use HTTPS';
  }
  if (/localhost|127\.0\.0\.1|10\.0\.2\.2|192\.168\./i.test(trimmed)) {
    return 'Production API must not target development hosts';
  }
  if (!trimmed.includes('/api/v1')) {
    return 'Production API URL should include the /api/v1 prefix';
  }
  return null;
}
