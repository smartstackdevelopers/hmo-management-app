import { Platform } from 'react-native';
import Constants from 'expo-constants';

/** Dev machine hostname for emulator / Expo Go (not legacy API port). */
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