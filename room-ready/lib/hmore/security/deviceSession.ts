/**
 * Registers this installation with the API after Auth0 has already signed the user in.
 * A revoked installation id is discarded. The next attempt uses a new id.
 * The request body is installation metadata only.
 */

import { HmoreApiError, hmoreRequest } from '@/lib/hmore/client';
import {
  isInstallationRevokedError,
  resetDeviceSessionRevokeState,
} from '@/lib/hmore/security/deviceSessionRevoke';
import {
  clearDeviceSessionIds,
  readDeviceSessionStatus,
  readInstallationId,
  writeDeviceSessionId,
  writeDeviceSessionStatus,
  writeInstallationId,
} from '@/lib/hmore/security/deviceSessionStore';

export type DeviceSessionStatus = 'active' | 'revoked' | 'lost';

export type DeviceSessionRecord = {
  id: string;
  organisation_id: string;
  user_id: string;
  installation_id: string;
  platform: 'ios' | 'android' | 'web';
  device_name: string | null;
  app_version: string | null;
  status: DeviceSessionStatus;
  revoked_at: string | null;
  revoked_by_user_id: string | null;
  revocation_reason: string | null;
  last_seen_at: string | null;
  created_at: string | null;
  is_current?: boolean;
};

export function devicePlatform(os: string): 'ios' | 'android' | 'web' {
  if (os === 'ios' || os === 'android' || os === 'web') return os;
  return 'web';
}

export function deviceSessionRegisterBody(input: {
  installationId: string;
  platform: 'ios' | 'android' | 'web';
  deviceName?: string | null;
  appVersion?: string | null;
}): { installation_id: string; platform: 'ios' | 'android' | 'web'; device_name?: string; app_version?: string } {
  const body: {
    installation_id: string;
    platform: 'ios' | 'android' | 'web';
    device_name?: string;
    app_version?: string;
  } = {
    installation_id: input.installationId,
    platform: input.platform,
  };
  if (input.deviceName && input.deviceName.trim()) body.device_name = input.deviceName.trim();
  if (input.appVersion && input.appVersion.trim()) body.app_version = input.appVersion.trim();
  return body;
}

function randomInstallationId(): string {
  try {
    const crypto = require('expo-crypto') as { randomUUID?: () => string };
    if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  } catch {
    // Fall through to another generator.
  }
  if (typeof globalThis.crypto?.randomUUID === 'function') return globalThis.crypto.randomUUID();
  const bytes = Array.from({ length: 16 }, () => Math.floor(Math.random() * 256));
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const hex = bytes.map((value) => value.toString(16).padStart(2, '0')).join('');
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}

async function ensureInstallationId(forceNew: boolean): Promise<string> {
  if (!forceNew) {
    const existing = await readInstallationId();
    if (existing) return existing;
  }
  const created = randomInstallationId();
  await writeInstallationId(created);
  return created;
}

function deviceName(): string | undefined {
  try {
    const Constants = require('expo-constants').default as { deviceName?: string | null };
    const name = Constants?.deviceName;
    return typeof name === 'string' && name.trim() ? name.trim() : undefined;
  } catch {
    return undefined;
  }
}

function appVersion(): string | undefined {
  try {
    const Constants = require('expo-constants').default as { expoConfig?: { version?: string } | null };
    const version = Constants?.expoConfig?.version;
    return typeof version === 'string' && version.trim() ? version.trim() : undefined;
  } catch {
    return undefined;
  }
}

export async function fetchCurrentDeviceSession(): Promise<DeviceSessionRecord> {
  return hmoreRequest<DeviceSessionRecord>('/device-sessions/current', { method: 'GET' });
}

export async function listDeviceSessions(): Promise<DeviceSessionRecord[]> {
  const data = await hmoreRequest<{ items: DeviceSessionRecord[] }>('/device-sessions', { method: 'GET' });
  return data.items ?? [];
}

export async function revokeDeviceSession(id: string, reason = 'user_sign_out'): Promise<DeviceSessionRecord> {
  return hmoreRequest<DeviceSessionRecord>(`/device-sessions/${id}/revoke`, {
    method: 'POST',
    body: { revocation_reason: reason },
  });
}

export async function reportDeviceSessionLost(id: string, reason = 'reported_lost'): Promise<DeviceSessionRecord> {
  return hmoreRequest<DeviceSessionRecord>(`/device-sessions/${id}/report-lost`, {
    method: 'POST',
    body: { revocation_reason: reason },
  });
}

export async function registerCurrentDeviceSession(options?: { forceNewInstallation?: boolean }): Promise<DeviceSessionRecord | null> {
  const status = await readDeviceSessionStatus();
  const replaceInstallation = options?.forceNewInstallation === true || status === 'revoked' || status === 'lost';
  if (status === 'revoked' || status === 'lost') {
    await clearDeviceSessionIds();
  }
  const { Platform } = require('react-native') as { Platform: { OS: string } };
  const installationId = await ensureInstallationId(replaceInstallation);
  const body = deviceSessionRegisterBody({
    installationId,
    platform: devicePlatform(Platform.OS),
    deviceName: deviceName(),
    appVersion: appVersion(),
  });
  try {
    const record = await hmoreRequest<DeviceSessionRecord>('/device-sessions', { method: 'POST', body });
    if (record.status !== 'active' || !record.id) return record;
    await writeDeviceSessionId(record.id);
    await writeInstallationId(record.installation_id || installationId);
    await writeDeviceSessionStatus('active');
    resetDeviceSessionRevokeState();
    return record;
  } catch (error) {
    if (isInstallationRevokedError(error) && !options?.forceNewInstallation) {
      return registerCurrentDeviceSession({ forceNewInstallation: true });
    }
    if (error instanceof HmoreApiError && error.status === 401 && error.detail === 'device_session_revoked') {
      return null;
    }
    throw error;
  }
}

export async function revokeCurrentDeviceSession(): Promise<void> {
  const { readDeviceSessionId } = await import('@/lib/hmore/security/deviceSessionStore');
  const id = await readDeviceSessionId();
  if (!id) return;
  await revokeDeviceSession(id, 'user_sign_out');
}
