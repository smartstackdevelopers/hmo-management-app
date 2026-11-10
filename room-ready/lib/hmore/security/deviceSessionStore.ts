/**
 * Device-session ids and the biometric preference live in SecureStore.
 * Tokens stay in the Auth0 SecureStore keys. This module does not import the draft storage package.
 * Biometric templates are never read or stored.
 */

type SecureStoreLike = {
  getItemAsync: (key: string) => Promise<string | null>;
  setItemAsync: (key: string, value: string) => Promise<void>;
  deleteItemAsync: (key: string) => Promise<void>;
};

export const BIOMETRIC_UNLOCK_KEY = 'hmore.biometric.unlock';
export const DEVICE_SESSION_ID_KEY = 'hmore.deviceSession.id';
export const DEVICE_INSTALLATION_ID_KEY = 'hmore.deviceSession.installationId';
export const DEVICE_SESSION_STATUS_KEY = 'hmore.deviceSession.status';

export type StoredDeviceSessionStatus = 'active' | 'revoked' | 'lost';

let sessionIdCache: string | null | undefined;
let installationIdCache: string | null | undefined;
let statusCache: string | null | undefined;

function secureStore(): SecureStoreLike | null {
  try {
    const loaded = require('expo-secure-store') as SecureStoreLike;
    if (!loaded || typeof loaded.getItemAsync !== 'function') return null;
    return loaded;
  } catch {
    return null;
  }
}

async function readKey(key: string): Promise<string | null> {
  const store = secureStore();
  if (!store) return null;
  try {
    const value = await store.getItemAsync(key);
    return value && value.trim() ? value : null;
  } catch {
    return null;
  }
}

async function writeKey(key: string, value: string): Promise<void> {
  const store = secureStore();
  if (!store) throw new Error('Secure storage is not available on this device.');
  await store.setItemAsync(key, value);
}

async function deleteKey(key: string): Promise<void> {
  const store = secureStore();
  if (!store) return;
  try {
    await store.deleteItemAsync(key);
  } catch {
    // Already absent.
  }
}

export function resetDeviceSessionStoreCache(): void {
  sessionIdCache = undefined;
  installationIdCache = undefined;
  statusCache = undefined;
}

export async function readBiometricUnlockEnabled(): Promise<boolean> {
  return (await readKey(BIOMETRIC_UNLOCK_KEY)) === '1';
}

export async function writeBiometricUnlockEnabled(enabled: boolean): Promise<void> {
  await writeKey(BIOMETRIC_UNLOCK_KEY, enabled ? '1' : '0');
}

export async function readDeviceSessionId(): Promise<string | null> {
  if (sessionIdCache !== undefined) return sessionIdCache;
  sessionIdCache = await readKey(DEVICE_SESSION_ID_KEY);
  return sessionIdCache;
}

export async function writeDeviceSessionId(value: string): Promise<void> {
  sessionIdCache = value;
  await writeKey(DEVICE_SESSION_ID_KEY, value);
}

export async function readInstallationId(): Promise<string | null> {
  if (installationIdCache !== undefined) return installationIdCache;
  installationIdCache = await readKey(DEVICE_INSTALLATION_ID_KEY);
  return installationIdCache;
}

export async function writeInstallationId(value: string): Promise<void> {
  installationIdCache = value;
  await writeKey(DEVICE_INSTALLATION_ID_KEY, value);
}

export async function readDeviceSessionStatus(): Promise<StoredDeviceSessionStatus | null> {
  if (statusCache !== undefined) {
    return statusCache === 'active' || statusCache === 'revoked' || statusCache === 'lost' ? statusCache : null;
  }
  const value = await readKey(DEVICE_SESSION_STATUS_KEY);
  statusCache = value;
  if (value === 'active' || value === 'revoked' || value === 'lost') return value;
  return null;
}

export async function writeDeviceSessionStatus(status: StoredDeviceSessionStatus): Promise<void> {
  statusCache = status;
  await writeKey(DEVICE_SESSION_STATUS_KEY, status);
}

/** Drops the session and installation ids. The status key is kept so a later sync can see the revoke. */
export async function clearDeviceSessionIds(): Promise<void> {
  sessionIdCache = null;
  installationIdCache = null;
  await deleteKey(DEVICE_SESSION_ID_KEY);
  await deleteKey(DEVICE_INSTALLATION_ID_KEY);
}
