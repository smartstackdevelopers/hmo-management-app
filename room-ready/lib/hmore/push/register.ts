import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { PermissionsAndroid, Platform } from 'react-native';

import { hmoreFetch } from '@/lib/hmore/client';
import { PUSH_PERMISSION_RATIONALE, registerDevicePush, resolveEasProjectId, type PushPlatform } from '@/lib/hmore/push/registerCore';

export const PUSH_DEVICE_STORAGE_KEY = '@hmore_push_device_id';

function platformName(): PushPlatform {
  if (Platform.OS === 'ios' || Platform.OS === 'android' || Platform.OS === 'web') return Platform.OS;
  return 'web';
}

async function requestWithRationale(): Promise<{ granted: boolean }> {
  if (Platform.OS === 'android' && Number(Platform.Version) >= 33) {
    const result = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.POST_NOTIFICATIONS, {
      title: 'Notifications',
      message: PUSH_PERMISSION_RATIONALE,
      buttonPositive: 'Allow',
      buttonNegative: 'Not now',
    });
    if (result !== PermissionsAndroid.RESULTS.GRANTED) return { granted: false };
  }
  const Notifications = await import('expo-notifications');
  const asked = await Notifications.requestPermissionsAsync();
  return { granted: asked.granted === true || asked.status === 'granted' };
}

/** Registers this install after an HMore session exists. Missing permission or EAS project id skips registration. */
export async function registerPushAfterSession(): Promise<{ registered: boolean; reason?: string }> {
  try {
    const Notifications = await import('expo-notifications');
    const projectId = resolveEasProjectId({
      envProjectId: process.env.EXPO_PUBLIC_EAS_PROJECT_ID,
      easConfigProjectId: Constants.easConfig?.projectId ?? null,
    });
    return await registerDevicePush({
      getPermission: async () => {
        const current = await Notifications.getPermissionsAsync();
        return { granted: current.granted === true || current.status === 'granted' };
      },
      requestPermission: requestWithRationale,
      getToken: async (id) => {
        const token = await Notifications.getExpoPushTokenAsync({ projectId: id });
        return token.data;
      },
      projectId,
      platform: platformName(),
      appVersion: Constants.expoConfig?.version ?? null,
      registerApi: (body) => hmoreFetch<{ id: string }>('/push/devices', { method: 'POST', body }),
      storeDeviceId: (id) => AsyncStorage.setItem(PUSH_DEVICE_STORAGE_KEY, id),
    });
  } catch {
    return { registered: false, reason: 'register_failed' };
  }
}

/** Deactivates the device stored for this install. Safe to call when nothing was registered. */
export async function deactivateRegisteredPush(): Promise<void> {
  const deviceId = await AsyncStorage.getItem(PUSH_DEVICE_STORAGE_KEY);
  if (!deviceId) return;
  try {
    await hmoreFetch(`/push/devices/${deviceId}`, { method: 'DELETE' });
  } catch {
    // Sign-out still proceeds. The token can be deactivated on the next register from another account.
  } finally {
    await AsyncStorage.removeItem(PUSH_DEVICE_STORAGE_KEY);
  }
}
