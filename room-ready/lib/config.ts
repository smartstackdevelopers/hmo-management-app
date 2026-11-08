import { Platform } from 'react-native';
import Constants from 'expo-constants';

export function resolveDevHost(): string {
  if (Platform.OS === 'android') return '10.0.2.2';
  if (Platform.OS === 'web') return 'localhost';

  const hostUri = Constants.expoConfig?.hostUri;
  if (hostUri) {
    const host = hostUri.split(':')[0];
    if (host && host !== 'localhost') return host;
  }
  return 'localhost';
}

export const API_BASE_URL =
  process.env.EXPO_PUBLIC_API_URL ?? `http://${resolveDevHost()}:3001`;

export function getFileUrl(path: string): string {
  if (path.startsWith('http')) return path;
  return `${API_BASE_URL}${path}`;
}
