/**
 * Cross-platform key/value storage for session secrets.
 * Native: expo-secure-store. Web / broken native module: AsyncStorage fallback.
 */
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Platform } from 'react-native';

type Store = {
  getItem: (key: string) => Promise<string | null>;
  setItem: (key: string, value: string) => Promise<void>;
  deleteItem: (key: string) => Promise<void>;
};

function canUseSecureStore(): boolean {
  if (Platform.OS === 'web') return false;
  try {
    // Lazy require so web bundling does not assume a native module.
    const SecureStore = require('expo-secure-store') as {
      getItemAsync?: (key: string) => Promise<string | null>;
      setItemAsync?: (key: string, value: string) => Promise<void>;
      deleteItemAsync?: (key: string) => Promise<void>;
    };
    return (
      typeof SecureStore.getItemAsync === 'function' &&
      typeof SecureStore.setItemAsync === 'function' &&
      typeof SecureStore.deleteItemAsync === 'function'
    );
  } catch {
    return false;
  }
}

function asyncStore(): Store {
  return {
    getItem: (key) => AsyncStorage.getItem(key),
    setItem: (key, value) => AsyncStorage.setItem(key, value),
    deleteItem: async (key) => {
      try {
        await AsyncStorage.removeItem(key);
      } catch {
        // Already absent.
      }
    },
  };
}

function nativeSecureStore(): Store {
  const SecureStore = require('expo-secure-store') as {
    getItemAsync: (key: string) => Promise<string | null>;
    setItemAsync: (key: string, value: string) => Promise<void>;
    deleteItemAsync: (key: string) => Promise<void>;
  };
  const fallback = asyncStore();
  return {
    getItem: async (key) => {
      try {
        return await SecureStore.getItemAsync(key);
      } catch {
        return fallback.getItem(key);
      }
    },
    setItem: async (key, value) => {
      try {
        await SecureStore.setItemAsync(key, value);
      } catch {
        await fallback.setItem(key, value);
      }
    },
    deleteItem: async (key) => {
      try {
        await SecureStore.deleteItemAsync(key);
      } catch {
        await fallback.deleteItem(key);
      }
    },
  };
}

export function getSecureStorage(): Store {
  return canUseSecureStore() ? nativeSecureStore() : asyncStore();
}

export async function secureGetItem(key: string): Promise<string | null> {
  return getSecureStorage().getItem(key);
}

export async function secureSetItem(key: string, value: string): Promise<void> {
  return getSecureStorage().setItem(key, value);
}

export async function secureDeleteItem(key: string): Promise<void> {
  return getSecureStorage().deleteItem(key);
}
