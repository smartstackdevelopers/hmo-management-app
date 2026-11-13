import { hmoreFetch } from '@/lib/hmore/client';

export function listPendingSignatures(): Promise<Record<string, unknown>[]> {
  return hmoreFetch<Record<string, unknown>[]>('/digital-id-esign/signing-requests/mine', { method: 'GET' });
}

export function getIdentityStatus(): Promise<Record<string, unknown>> {
  return hmoreFetch<Record<string, unknown>>('/digital-id-esign/identity/me', { method: 'GET' });
}
