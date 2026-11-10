import { hmoreFetch } from '@/lib/hmore/client';

type NetInfoLike = {
  fetch: () => Promise<{ isConnected?: boolean | null; isInternetReachable?: boolean | null }>;
};

export function loadNetInfo(): NetInfoLike | null {
  try {
    const mod = require('@react-native-community/netinfo') as { default?: NetInfoLike } & Partial<NetInfoLike>;
    const candidate = mod.default ?? (typeof mod.fetch === 'function' ? (mod as NetInfoLike) : null);
    if (candidate && typeof candidate.fetch === 'function') return candidate;
    return null;
  } catch {
    return null;
  }
}

export async function pingHmoreHealth(): Promise<boolean> {
  try {
    await hmoreFetch<{ status?: string }>('/health', { method: 'GET' });
    return true;
  } catch {
    return false;
  }
}

export async function isDeviceOnline(options?: {
  netInfo?: NetInfoLike | null;
  ping?: () => Promise<boolean>;
}): Promise<boolean> {
  const netInfo = options && 'netInfo' in options ? options.netInfo : loadNetInfo();
  if (netInfo) {
    try {
      const state = await netInfo.fetch();
      if (state.isConnected === false || state.isInternetReachable === false) return false;
      if (state.isConnected === true || state.isInternetReachable === true) return true;
    } catch {
      // Fall through to the health ping.
    }
  }
  if (options?.ping) return options.ping();
  return pingHmoreHealth();
}
