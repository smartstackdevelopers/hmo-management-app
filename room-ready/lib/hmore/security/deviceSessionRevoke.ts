/**
 * Local cleanup when the API says this device session is no longer active.
 * Offline drafts are left in place. They stay bound to the user that saved them.
 */

import { clearRequestContext } from '@/lib/hmore/requestContext';
import { haltOfflineSync, resumeOfflineSync } from '@/lib/hmore/security/deviceSessionGate';
import {
  clearDeviceSessionIds,
  writeDeviceSessionStatus,
} from '@/lib/hmore/security/deviceSessionStore';
import { clearToken } from '@/lib/api';
import { clearAuth0Tokens, revokeAuth0RefreshToken } from '@/lib/hmoreAuth0';

export const REMOTE_SIGNOUT_MESSAGE =
  'This device was signed out. Sign in with your organisation account. Offline drafts stay on this phone until that same account signs in again.';

type Listener = () => void;

let message: string | null = null;
const messageListeners = new Set<(value: string | null) => void>();
const endedListeners = new Set<Listener>();
let ending: Promise<void> | null = null;

export function deviceSessionRevokedMessage(): string | null {
  return message;
}

export function setDeviceSessionRevokedMessage(value: string | null): void {
  message = value;
  messageListeners.forEach((listener) => listener(value));
}

export function subscribeDeviceSessionRevokedMessage(listener: (value: string | null) => void): () => void {
  messageListeners.add(listener);
  listener(message);
  return () => {
    messageListeners.delete(listener);
  };
}

export function subscribeLocalSessionEnded(listener: Listener): () => void {
  endedListeners.add(listener);
  return () => {
    endedListeners.delete(listener);
  };
}

export function isDeviceSessionRevokedError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false;
  const record = error as { status?: unknown; detail?: unknown };
  return record.status === 401 && record.detail === 'device_session_revoked';
}

export function isInstallationRevokedError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false;
  const record = error as { status?: unknown; detail?: unknown };
  return record.status === 403 && record.detail === 'session_revoked';
}

export async function endLocalSession(options?: { message?: string | null }): Promise<void> {
  if (ending) return ending;
  ending = (async () => {
    haltOfflineSync();
    if (options?.message) setDeviceSessionRevokedMessage(options.message);
    try {
      await revokeAuth0RefreshToken();
    } catch {
      // The refresh token may already be gone. Local cleanup still continues.
    }
    await writeDeviceSessionStatus('revoked');
    await clearDeviceSessionIds();
    await clearAuth0Tokens();
    await clearRequestContext();
    await clearToken();
    endedListeners.forEach((listener) => listener());
  })();
  try {
    await ending;
  } finally {
    ending = null;
  }
}

export async function handleRemoteDeviceSessionRevoked(): Promise<void> {
  await endLocalSession({ message: REMOTE_SIGNOUT_MESSAGE });
}

export function resetDeviceSessionRevokeState(): void {
  ending = null;
  resumeOfflineSync();
  setDeviceSessionRevokedMessage(null);
}
