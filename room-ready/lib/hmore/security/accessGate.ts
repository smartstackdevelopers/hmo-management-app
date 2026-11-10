/** In-memory lock used by push deep links. The OS prompt result is what clears it. */

import { readDeviceSessionStatus } from '@/lib/hmore/security/deviceSessionStore';
import { isOfflineSyncHalted } from '@/lib/hmore/security/deviceSessionGate';

let biometricLocked = false;

export function setBiometricLocked(locked: boolean): void {
  biometricLocked = locked;
}

export function isBiometricLocked(): boolean {
  return biometricLocked;
}

export async function protectedNavigationBlocked(): Promise<boolean> {
  if (biometricLocked || isOfflineSyncHalted()) return true;
  try {
    const status = await readDeviceSessionStatus();
    return status === 'revoked' || status === 'lost';
  } catch {
    return biometricLocked;
  }
}
