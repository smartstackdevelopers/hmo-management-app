/**
 * OS biometric unlock for an Auth0 session that is already on this device.
 * The preference is a SecureStore flag. Fingerprint and face data stay in the OS.
 */

import { readBiometricUnlockEnabled, writeBiometricUnlockEnabled } from '@/lib/hmore/security/deviceSessionStore';

export type BiometricAvailability = {
  supported: boolean;
  enrolled: boolean;
  reason: 'ok' | 'unsupported' | 'not_enrolled' | 'unavailable';
};

type LocalAuthenticationModule = {
  hasHardwareAsync: () => Promise<boolean>;
  isEnrolledAsync: () => Promise<boolean>;
  authenticateAsync: (options?: {
    promptMessage?: string;
    cancelLabel?: string;
    disableDeviceFallback?: boolean;
  }) => Promise<{ success: boolean }>;
};

function localAuthentication(): LocalAuthenticationModule | null {
  try {
    const loaded = require('expo-local-authentication') as LocalAuthenticationModule;
    if (!loaded || typeof loaded.authenticateAsync !== 'function') return null;
    return loaded;
  } catch {
    return null;
  }
}

export async function getBiometricAvailability(): Promise<BiometricAvailability> {
  const local = localAuthentication();
  if (!local) return { supported: false, enrolled: false, reason: 'unavailable' };
  try {
    const supported = await local.hasHardwareAsync();
    if (!supported) return { supported: false, enrolled: false, reason: 'unsupported' };
    const enrolled = await local.isEnrolledAsync();
    if (!enrolled) return { supported: true, enrolled: false, reason: 'not_enrolled' };
    return { supported: true, enrolled: true, reason: 'ok' };
  } catch {
    return { supported: false, enrolled: false, reason: 'unavailable' };
  }
}

/** True only when the OS reports a successful biometric prompt. Preference is not consulted. */
export function grantUnlock(osSuccess: boolean): boolean {
  return osSuccess === true;
}

export async function authenticateAsync(): Promise<boolean> {
  const availability = await getBiometricAvailability();
  if (!availability.enrolled) return false;
  const local = localAuthentication();
  if (!local) return false;
  try {
    const result = await local.authenticateAsync({
      promptMessage: 'Unlock HMore',
      cancelLabel: 'Cancel',
      disableDeviceFallback: true,
    });
    return grantUnlock(result.success === true);
  } catch {
    return false;
  }
}

export async function isBiometricUnlockEnabled(): Promise<boolean> {
  return readBiometricUnlockEnabled();
}

/**
 * Turning the preference on requires a successful OS prompt first.
 * A failed or cancelled prompt leaves the stored preference unchanged.
 */
export async function setBiometricUnlockEnabled(enabled: boolean): Promise<boolean> {
  if (enabled) {
    const availability = await getBiometricAvailability();
    if (!availability.enrolled) return false;
    const success = await authenticateAsync();
    if (!grantUnlock(success)) return false;
  }
  await writeBiometricUnlockEnabled(enabled);
  return true;
}
