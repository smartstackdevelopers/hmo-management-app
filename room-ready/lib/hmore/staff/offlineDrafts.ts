/**
 * Offline staff drafts.
 *
 * SecureStore items are limited to about 2048 bytes. A daily note can be up to
 * 20,000 characters, so the draft payload is not stored there.
 *
 * A random 32-byte key is kept in SecureStore. The draft list is XOR-encrypted
 * with that key and stored in AsyncStorage. This hides drafts from a casual
 * read of AsyncStorage. It is not a substitute for device encryption, and anyone
 * who can read both stores can decrypt the drafts.
 *
 * The API has no `client_request_id`. Drafts keep one locally. After a 2xx
 * response the draft is removed by its id so a later sync does not send it again.
 * A lost response can still duplicate if the user retries; the editor disables
 * the button while a request is in flight.
 */

export type DraftType = 'daily_log' | 'visit_update' | 'task_update' | 'work_order_update';

export interface StaffDraft {
  id: string;
  type: DraftType;
  payload: Record<string, unknown>;
  clientRequestId: string;
  createdAt: string;
  updatedAt: string;
  syncState: 'pending' | 'error';
  lastError?: string;
}

export interface DraftStorage {
  getSecure: (key: string) => Promise<string | null>;
  setSecure: (key: string, value: string) => Promise<void>;
  getItem: (key: string) => Promise<string | null>;
  setItem: (key: string, value: string) => Promise<void>;
  removeItem: (key: string) => Promise<void>;
}

const SECURE_KEY = 'hmore.staff.draft.v1.key';
const ASYNC_KEY = 'hmore.staff.drafts.v1';
const syncingIds = new Set<string>();

export interface SyncResultItem {
  id: string;
  saved: boolean;
  status: number;
  error?: string;
}

function createId(): string {
  const cryptoApi = globalThis.crypto;
  if (cryptoApi && typeof cryptoApi.randomUUID === 'function') return cryptoApi.randomUUID();
  return `draft-${Date.now().toString(16)}-${Math.random().toString(16).slice(2)}`;
}

function bytesToBase64(bytes: Uint8Array): string {
  let binary = '';
  for (let index = 0; index < bytes.length; index += 1) binary += String.fromCharCode(bytes[index]);
  if (typeof globalThis.btoa === 'function') return globalThis.btoa(binary);
  return Buffer.from(bytes).toString('base64');
}

function base64ToBytes(value: string): Uint8Array {
  const binary = typeof globalThis.atob === 'function' ? globalThis.atob(value) : Buffer.from(value, 'base64').toString('binary');
  const bytes = new Uint8Array(binary.length);
  for (let index = 0; index < binary.length; index += 1) bytes[index] = binary.charCodeAt(index);
  return bytes;
}

function xorBytes(data: Uint8Array, key: Uint8Array): Uint8Array {
  const out = new Uint8Array(data.length);
  for (let index = 0; index < data.length; index += 1) out[index] = data[index] ^ key[index % key.length];
  return out;
}

async function randomKey(): Promise<Uint8Array> {
  try {
    const cryptoModule = require('expo-crypto') as { getRandomBytesAsync?: (size: number) => Promise<Uint8Array> };
    if (cryptoModule.getRandomBytesAsync) return new Uint8Array(await cryptoModule.getRandomBytesAsync(32));
  } catch {
    // Tests and unsupported runtimes fall through to Web Crypto or Math.random.
  }
  const bytes = new Uint8Array(32);
  if (globalThis.crypto?.getRandomValues) {
    globalThis.crypto.getRandomValues(bytes);
    return bytes;
  }
  for (let index = 0; index < bytes.length; index += 1) bytes[index] = Math.floor(Math.random() * 256);
  return bytes;
}

async function getOrCreateKey(store: DraftStorage): Promise<Uint8Array> {
  const existing = await store.getSecure(SECURE_KEY);
  if (existing) {
    const key = base64ToBytes(existing);
    if (key.length >= 16) return key;
  }
  const key = await randomKey();
  await store.setSecure(SECURE_KEY, bytesToBase64(key));
  return key;
}

function encodeText(value: string): Uint8Array {
  return new TextEncoder().encode(value);
}

function decodeText(bytes: Uint8Array): string {
  return new TextDecoder().decode(bytes);
}

export function draftResourceKey(type: DraftType, payload: Record<string, unknown>): string {
  const target =
    payload.visit_id ?? payload.task_id ?? payload.request_id ?? payload.tenant_id ?? payload.id ?? '';
  return `${type}:${String(target)}`;
}

function isDraft(value: unknown): value is StaffDraft {
  if (!value || typeof value !== 'object') return false;
  const draft = value as StaffDraft;
  return typeof draft.id === 'string' && typeof draft.type === 'string' && !!draft.payload && typeof draft.clientRequestId === 'string';
}

let defaultStorage: DraftStorage | null = null;

export function createDefaultDraftStorage(): DraftStorage {
  return {
    getSecure: async (key) => {
      const SecureStore = require('expo-secure-store') as { getItemAsync: (key: string) => Promise<string | null> };
      return SecureStore.getItemAsync(key);
    },
    setSecure: async (key, value) => {
      const SecureStore = require('expo-secure-store') as { setItemAsync: (key: string, value: string) => Promise<void> };
      await SecureStore.setItemAsync(key, value);
    },
    getItem: async (key) => {
      const AsyncStorage = require('@react-native-async-storage/async-storage') as {
        getItem: (key: string) => Promise<string | null>;
      };
      return AsyncStorage.getItem(key);
    },
    setItem: async (key, value) => {
      const AsyncStorage = require('@react-native-async-storage/async-storage') as {
        setItem: (key: string, value: string) => Promise<void>;
      };
      await AsyncStorage.setItem(key, value);
    },
    removeItem: async (key) => {
      const AsyncStorage = require('@react-native-async-storage/async-storage') as {
        removeItem: (key: string) => Promise<void>;
      };
      await AsyncStorage.removeItem(key);
    },
  };
}

function resolveStore(store?: DraftStorage): DraftStorage {
  if (store) return store;
  if (!defaultStorage) defaultStorage = createDefaultDraftStorage();
  return defaultStorage;
}

async function readAll(store: DraftStorage): Promise<StaffDraft[]> {
  const raw = await store.getItem(ASYNC_KEY);
  if (!raw) return [];
  const parsed = JSON.parse(raw) as { v?: number; ciphertext?: string };
  if (!parsed.ciphertext) throw new Error('Drafts on this device could not be read.');
  const key = await getOrCreateKey(store);
  const plain = decodeText(xorBytes(base64ToBytes(parsed.ciphertext), key));
  const drafts = JSON.parse(plain) as unknown;
  if (!Array.isArray(drafts) || !drafts.every(isDraft)) throw new Error('Drafts on this device could not be read.');
  return drafts;
}

async function writeAll(store: DraftStorage, drafts: StaffDraft[]): Promise<void> {
  if (drafts.length === 0) {
    await store.removeItem(ASYNC_KEY);
    return;
  }
  const key = await getOrCreateKey(store);
  const ciphertext = bytesToBase64(xorBytes(encodeText(JSON.stringify(drafts)), key));
  await store.setItem(ASYNC_KEY, JSON.stringify({ v: 1, ciphertext }));
}

export async function loadDrafts(store?: DraftStorage): Promise<StaffDraft[]> {
  return readAll(resolveStore(store));
}

export async function saveDraft(
  input: { type: DraftType; payload: Record<string, unknown> },
  store?: DraftStorage,
): Promise<StaffDraft> {
  const resolved = resolveStore(store);
  const drafts = await readAll(resolved);
  const key = draftResourceKey(input.type, input.payload);
  const existing = drafts.find((draft) => draftResourceKey(draft.type, draft.payload) === key);
  const now = new Date().toISOString();
  const next: StaffDraft = {
    id: existing?.id ?? createId(),
    type: input.type,
    payload: input.payload,
    clientRequestId: existing?.clientRequestId ?? createId(),
    createdAt: existing?.createdAt ?? now,
    updatedAt: now,
    syncState: 'pending',
  };
  await writeAll(resolved, [...drafts.filter((draft) => draft.id !== next.id), next]);
  return next;
}

export async function clearDraft(id: string, store?: DraftStorage): Promise<void> {
  const resolved = resolveStore(store);
  const drafts = await readAll(resolved);
  await writeAll(
    resolved,
    drafts.filter((draft) => draft.id !== id),
  );
}

export async function markDraftError(id: string, error: string, store?: DraftStorage): Promise<void> {
  const resolved = resolveStore(store);
  const drafts = await readAll(resolved);
  await writeAll(
    resolved,
    drafts.map((draft) => (draft.id === id ? { ...draft, syncState: 'error' as const, lastError: error, updatedAt: new Date().toISOString() } : draft)),
  );
}

export async function syncDrafts(
  submit: (draft: StaffDraft) => Promise<{ status: number; error?: string }>,
  isOnline: () => Promise<boolean>,
  store?: DraftStorage,
): Promise<{ offline: boolean; results: SyncResultItem[] }> {
  if (!(await isOnline())) return { offline: true, results: [] };
  const resolved = resolveStore(store);
  const drafts = await readAll(resolved);
  const results: SyncResultItem[] = [];
  for (const draft of drafts) {
    if (syncingIds.has(draft.id)) continue;
    syncingIds.add(draft.id);
    try {
      const response = await submit(draft);
      const saved = response.status >= 200 && response.status < 300;
      if (saved) await clearDraft(draft.id, resolved);
      else await markDraftError(draft.id, response.error || `Not saved (${response.status})`, resolved);
      results.push({ id: draft.id, saved, status: response.status, error: saved ? undefined : response.error });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not reach HMore. The draft is still on this device.';
      await markDraftError(draft.id, message, resolved);
      results.push({ id: draft.id, saved: false, status: 0, error: message });
    } finally {
      syncingIds.delete(draft.id);
    }
  }
  return { offline: false, results };
}
