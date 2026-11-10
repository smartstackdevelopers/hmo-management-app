/**
 * Stops offline sync when this installation is revoked or reported lost.
 * A missing session id means the device has not registered yet, so F4.5 sync still runs.
 * If the status check cannot reach the API, the last stored status is used.
 * A revoke that happens while the phone is offline is applied on the next successful check.
 */

import { readDeviceSessionId, readDeviceSessionStatus } from '@/lib/hmore/security/deviceSessionStore';

let syncHalted = false;

export function haltOfflineSync(): void {
  syncHalted = true;
}

export function resumeOfflineSync(): void {
  syncHalted = false;
}

export function isOfflineSyncHalted(): boolean {
  return syncHalted;
}

export async function deviceSessionAllowsSync(): Promise<boolean> {
  if (syncHalted) return false;
  let status: string | null = null;
  try {
    status = await readDeviceSessionStatus();
  } catch {
    status = null;
  }
  if (status === 'revoked' || status === 'lost') {
    syncHalted = true;
    return false;
  }
  let sessionId: string | null = null;
  try {
    sessionId = await readDeviceSessionId();
  } catch {
    sessionId = null;
  }
  if (!sessionId) return true;
  try {
    const { fetchCurrentDeviceSession } = await import('@/lib/hmore/security/deviceSession');
    const current = await fetchCurrentDeviceSession();
    if (current.status === 'active') return true;
    const { handleRemoteDeviceSessionRevoked } = await import('@/lib/hmore/security/deviceSessionRevoke');
    await handleRemoteDeviceSessionRevoked();
    return false;
  } catch (error) {
    const { isDeviceSessionRevokedError } = await import('@/lib/hmore/security/deviceSessionRevoke');
    if (isDeviceSessionRevokedError(error)) return false;
    return true;
  }
}
