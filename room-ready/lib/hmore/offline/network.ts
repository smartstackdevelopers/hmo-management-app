import { hmoreFetch } from '@/lib/hmore/client';

export type Connectivity = 'online' | 'offline' | 'unstable';

export type NetInfoState = {
  isConnected?: boolean | null;
  isInternetReachable?: boolean | null;
};

export type NetInfoLike = {
  fetch: () => Promise<NetInfoState>;
  addEventListener?: (listener: (state: NetInfoState) => void) => () => void;
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

function deviceConnected(state: NetInfoState): boolean | null {
  if (state.isConnected === false || state.isInternetReachable === false) return false;
  if (state.isConnected === true || state.isInternetReachable === true) return true;
  return null;
}

/**
 * Online means the device has a network and the API health check succeeded.
 * Unstable means the device has a network and the health check failed.
 * Offline means the device reports no connection, or neither signal is available.
 */
export async function readConnectivity(options?: {
  netInfo?: NetInfoLike | null;
  ping?: () => Promise<boolean>;
}): Promise<Connectivity> {
  const netInfo = options && 'netInfo' in options ? options.netInfo : loadNetInfo();
  let connected: boolean | null = null;
  if (netInfo) {
    try {
      connected = deviceConnected(await netInfo.fetch());
    } catch {
      connected = null;
    }
  }
  if (connected === false) return 'offline';
  const ping = options && 'ping' in options ? options.ping : pingHmoreHealth;
  if (!ping) return connected === true ? 'online' : 'offline';
  const healthy = await ping().catch(() => false);
  if (healthy) return 'online';
  return connected === true ? 'unstable' : 'offline';
}

export async function isDeviceOnline(options?: {
  netInfo?: NetInfoLike | null;
  ping?: () => Promise<boolean>;
}): Promise<boolean> {
  return (await readConnectivity(options)) === 'online';
}

/** Auto-sync runs once when a connection returns. It does not poll in the background. */
export function shouldSyncOnReconnect(previous: Connectivity | null, next: Connectivity): boolean {
  return next === 'online' && previous !== null && previous !== 'online';
}

export function scheduleReconnectSync(run: () => Promise<unknown>, delayMs = 1500): () => void {
  const timer = setTimeout(() => {
    void run();
  }, delayMs);
  return () => clearTimeout(timer);
}
