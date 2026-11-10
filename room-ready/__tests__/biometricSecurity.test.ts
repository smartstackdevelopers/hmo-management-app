import { readFileSync } from 'fs';
import path from 'path';

import * as LocalAuthentication from 'expo-local-authentication';

import { hmoreRequest } from '@/lib/hmore/client';
import { syncNow } from '@/lib/hmore/offline/syncEngine';
import type { DraftStorage } from '@/lib/hmore/offline/store';
import { handlePushOpen } from '@/lib/hmore/push/links';
import { setBiometricLocked } from '@/lib/hmore/security/accessGate';
import { authenticateAsync, grantUnlock, setBiometricUnlockEnabled } from '@/lib/hmore/security/biometrics';
import { deviceSessionRegisterBody } from '@/lib/hmore/security/deviceSession';
import { resumeOfflineSync } from '@/lib/hmore/security/deviceSessionGate';
import { resetDeviceSessionRevokeState } from '@/lib/hmore/security/deviceSessionRevoke';
import {
  BIOMETRIC_UNLOCK_KEY,
  resetDeviceSessionStoreCache,
  writeDeviceSessionStatus,
} from '@/lib/hmore/security/deviceSessionStore';
import * as SecureStore from 'expo-secure-store';

jest.mock('expo-local-authentication', () => ({
  hasHardwareAsync: jest.fn(async () => true),
  isEnrolledAsync: jest.fn(async () => true),
  authenticateAsync: jest.fn(async () => ({ success: true })),
}));

jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(),
  setItemAsync: jest.fn(),
  deleteItemAsync: jest.fn(),
}));

const secure = new Map<string, string>();

function emptyStore(): DraftStorage {
  return {
    getSecure: async () => null,
    setSecure: async () => undefined,
    getItem: async () => null,
    setItem: async () => undefined,
    removeItem: async () => undefined,
  };
}

beforeEach(() => {
  secure.clear();
  resetDeviceSessionStoreCache();
  resetDeviceSessionRevokeState();
  resumeOfflineSync();
  setBiometricLocked(false);
  (SecureStore.getItemAsync as jest.Mock).mockImplementation(async (key: string) => secure.get(key) ?? null);
  (SecureStore.setItemAsync as jest.Mock).mockImplementation(async (key: string, value: string) => {
    secure.set(key, value);
  });
  (SecureStore.deleteItemAsync as jest.Mock).mockImplementation(async (key: string) => {
    secure.delete(key);
  });
  (LocalAuthentication.hasHardwareAsync as jest.Mock).mockReset();
  (LocalAuthentication.isEnrolledAsync as jest.Mock).mockReset();
  (LocalAuthentication.authenticateAsync as jest.Mock).mockReset();
  (LocalAuthentication.hasHardwareAsync as jest.Mock).mockResolvedValue(true);
  (LocalAuthentication.isEnrolledAsync as jest.Mock).mockResolvedValue(true);
  (LocalAuthentication.authenticateAsync as jest.Mock).mockResolvedValue({ success: true });
});

describe('biometric unlock', () => {
  it('stores only an on/off flag in SecureStore and never unlocks from that flag alone', async () => {
    const source = readFileSync(path.join(__dirname, '../lib/hmore/security/biometrics.ts'), 'utf8');
    const storeSource = readFileSync(path.join(__dirname, '../lib/hmore/security/deviceSessionStore.ts'), 'utf8');
    expect(source).not.toContain('@react-native-async-storage');
    expect(storeSource).not.toContain('@react-native-async-storage');
    expect(storeSource).not.toContain('accessToken');

    expect(grantUnlock(false)).toBe(false);
    expect(grantUnlock(true)).toBe(true);

    (LocalAuthentication.authenticateAsync as jest.Mock).mockResolvedValue({ success: false });
    await expect(setBiometricUnlockEnabled(true)).resolves.toBe(false);
    expect(secure.get(BIOMETRIC_UNLOCK_KEY)).toBeUndefined();

    (LocalAuthentication.authenticateAsync as jest.Mock).mockResolvedValue({ success: true });
    await expect(setBiometricUnlockEnabled(true)).resolves.toBe(true);
    expect(secure.get(BIOMETRIC_UNLOCK_KEY)).toBe('1');
    await expect(authenticateAsync()).resolves.toBe(true);
    expect(LocalAuthentication.authenticateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ disableDeviceFallback: true }),
    );
  });

  it('does not enable biometric unlock when the device has none enrolled', async () => {
    (LocalAuthentication.isEnrolledAsync as jest.Mock).mockResolvedValue(false);
    await expect(setBiometricUnlockEnabled(true)).resolves.toBe(false);
    expect(LocalAuthentication.authenticateAsync).not.toHaveBeenCalled();
    expect(secure.get(BIOMETRIC_UNLOCK_KEY)).toBeUndefined();
  });
});

describe('device session client', () => {
  it('registers installation metadata and does not send biometric fields', () => {
    const body = deviceSessionRegisterBody({
      installationId: '11111111-1111-4111-8111-111111111111',
      platform: 'ios',
      deviceName: 'Phone',
      appVersion: '1.0.0',
    });
    expect(Object.keys(body).sort()).toEqual(['app_version', 'device_name', 'installation_id', 'platform']);
    expect(JSON.stringify(body)).not.toContain('fingerprint');
    expect(JSON.stringify(body)).not.toContain('biometric');
  });

  it('sends the device session header and clears the session on revoke', async () => {
    const onDeviceSessionRevoked = jest.fn(async () => undefined);
    const fetchImpl = jest.fn(async () => new Response(JSON.stringify({ detail: 'device_session_revoked' }), { status: 401 }));
    await expect(
      hmoreRequest(
        '/tenants',
        { method: 'GET' },
        {
          getAccessToken: async () => 'token',
          getContext: () => ({ organisationId: 'org-1', role: 'tenant' }),
          fetchImpl: fetchImpl as unknown as typeof fetch,
          baseUrl: 'http://api.test/api/v1',
          getDeviceSessionId: async () => 'session-1',
          onDeviceSessionRevoked,
        },
      ),
    ).rejects.toMatchObject({ status: 401, detail: 'device_session_revoked' });
    const headers = (fetchImpl.mock.calls[0] as unknown as [string, RequestInit])[1].headers as Record<string, string>;
    expect(headers['X-Device-Session-Id']).toBe('session-1');
    expect(headers.Authorization).toBe('Bearer token');
    expect(onDeviceSessionRevoked).toHaveBeenCalledTimes(1);
  });
});

describe('protected navigation and sync', () => {
  it('does not open a push target while the biometric lock is up or the device is revoked', async () => {
    const navigate = jest.fn();
    const markRead = jest.fn();
    setBiometricLocked(true);
    await expect(
      handlePushOpen({ related_resource_type: 'incident', related_resource_id: '11111111-1111-4111-8111-111111111111' }, true, {
        navigate,
        markRead,
      }),
    ).resolves.toBe('');
    expect(navigate).not.toHaveBeenCalled();
    expect(markRead).not.toHaveBeenCalled();

    setBiometricLocked(false);
    await writeDeviceSessionStatus('revoked');
    await expect(
      handlePushOpen({ related_resource_type: 'maintenance_request', related_resource_id: '22222222-2222-4222-8222-222222222222' }, false, {
        navigate,
        markRead,
      }),
    ).resolves.toBe('');
    expect(navigate).not.toHaveBeenCalled();
  });

  it('skips sync when the device session is revoked and leaves the submit callback unused', async () => {
    const submit = jest.fn(async () => ({ status: 200 }));
    await writeDeviceSessionStatus('revoked');
    const blocked = await syncNow({
      submit,
      isOnline: async () => true,
      store: emptyStore(),
    });
    expect(blocked).toEqual({ offline: false, results: [], blockedReason: 'device_session_revoked' });
    expect(submit).not.toHaveBeenCalled();

    const allowed = await syncNow({
      submit,
      isOnline: async () => true,
      store: emptyStore(),
      deviceSessionAllowsSync: async () => true,
    });
    expect(allowed.offline).toBe(false);
    expect(submit).not.toHaveBeenCalled();
  });
});

describe('app config', () => {
  it('includes the Expo 57 local authentication plugin', () => {
    const app = JSON.parse(readFileSync(path.join(__dirname, '../app.json'), 'utf8')) as {
      expo: { plugins: unknown[]; ios: { infoPlist: Record<string, string> } };
    };
    const plugin = app.expo.plugins.find(
      (item) => Array.isArray(item) && item[0] === 'expo-local-authentication',
    );
    expect(plugin).toBeTruthy();
    expect(app.expo.ios.infoPlist.NSFaceIDUsageDescription).toContain('already signed in');
  });
});
