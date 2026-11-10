/**
 * Offline draft store.
 *
 * SecureStore items are limited to about 2048 bytes, so the draft list is not
 * stored there. A random 32-byte key stays in SecureStore. The draft list is
 * XOR-encrypted with that key and stored in AsyncStorage. This hides drafts
 * from a casual read of AsyncStorage. It is not a substitute for device
 * encryption: anyone who can read both stores can decrypt the drafts.
 *
 * Drafts are bound to a user id and an organisation id. A different account
 * cannot read them. Switching accounts deletes the previous account's draft
 * payload. Drafts saved before this binding existed are removed rather than
 * shown to whoever signs in next.
 */

export type DraftType = 'daily_log' | 'visit_update' | 'task_update' | 'work_order_update' | 'repair_create';

export type SyncState = 'draft' | 'pending' | 'syncing' | 'synced' | 'failed' | 'conflict' | 'needs_attention';

export interface DraftOwner {
  userId: string;
  organisationId: string;
}

export interface OfflineDraft {
  id: string;
  clientRequestId: string;
  type: DraftType;
  payload: Record<string, unknown>;
  localAttachmentUris: string[];
  syncState: SyncState;
  lastError?: string;
  serverUpdatedAt?: string;
  localUpdatedAt: string;
  serverResourceId?: string;
  createdAt: string;
  /** Same instant as localUpdatedAt. Kept so earlier callers can still read it. */
  updatedAt: string;
}

export interface DraftStorage {
  getSecure: (key: string) => Promise<string | null>;
  setSecure: (key: string, value: string) => Promise<void>;
  getItem: (key: string) => Promise<string | null>;
  setItem: (key: string, value: string) => Promise<void>;
  removeItem: (key: string) => Promise<void>;
}

export class DraftAccountError extends Error {
  constructor(message = 'These drafts belong to a different account.') {
    super(message);
    this.name = 'DraftAccountError';
  }
}

const SECURE_KEY = 'hmore.staff.draft.v1.key';
const LEGACY_KEY = 'hmore.staff.drafts.v1';
const OWNER_POINTER = 'hmore.offline.owner.v1';
const SECRET_KEYS = ['password', 'currentPassword', 'newPassword', 'access_token', 'refresh_token', 'authorization'];

export interface SaveDraftInput {
  type: DraftType;
  payload: Record<string, unknown>;
  localAttachmentUris?: string[];
  serverUpdatedAt?: string;
  serverResourceId?: string;
  syncState?: SyncState;
  lastError?: string;
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

export function sameOwner(left: DraftOwner, right: DraftOwner): boolean {
  return left.userId === right.userId && left.organisationId === right.organisationId;
}

export function draftStorageKey(owner: DraftOwner): string {
  const user = owner.userId.replace(/[^a-zA-Z0-9_-]/g, '');
  const organisation = owner.organisationId.replace(/[^a-zA-Z0-9_-]/g, '');
  return `hmore.offline.drafts.v2:${organisation}:${user}`;
}

export function draftResourceKey(type: DraftType, payload: Record<string, unknown>): string {
  if (type === 'repair_create') {
    return `${type}:${String(payload.property_id ?? '')}:${String(payload.title ?? '')}:${String(payload.description ?? '')}`;
  }
  const target = payload.visit_id ?? payload.task_id ?? payload.request_id ?? payload.tenant_id ?? payload.id ?? '';
  return `${type}:${String(target)}`;
}

export function stripDraftSecrets(payload: Record<string, unknown>): Record<string, unknown> {
  const next: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(payload)) {
    if (SECRET_KEYS.includes(key)) continue;
    next[key] = value;
  }
  return next;
}

function isDraft(value: unknown): value is OfflineDraft {
  if (!value || typeof value !== 'object') return false;
  const draft = value as OfflineDraft;
  return typeof draft.id === 'string' && typeof draft.type === 'string' && !!draft.payload && typeof draft.clientRequestId === 'string';
}

function normaliseDraft(value: OfflineDraft): OfflineDraft {
  const localUpdatedAt = value.localUpdatedAt || value.updatedAt || new Date().toISOString();
  return {
    ...value,
    localAttachmentUris: Array.isArray(value.localAttachmentUris) ? value.localAttachmentUris : [],
    syncState: value.syncState || 'pending',
    localUpdatedAt,
    updatedAt: value.updatedAt || localUpdatedAt,
    createdAt: value.createdAt || localUpdatedAt,
  };
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

function storageKey(owner?: DraftOwner): string {
  return owner ? draftStorageKey(owner) : LEGACY_KEY;
}

async function bindOwner(store: DraftStorage, owner: DraftOwner): Promise<void> {
  const raw = await store.getItem(OWNER_POINTER);
  if (raw) {
    try {
      const previous = JSON.parse(raw) as DraftOwner;
      if (previous.userId && previous.organisationId && !sameOwner(previous, owner)) {
        await store.removeItem(draftStorageKey(previous));
      }
    } catch {
      await store.removeItem(OWNER_POINTER);
    }
  }
  await store.removeItem(LEGACY_KEY);
  await store.setItem(OWNER_POINTER, JSON.stringify({ userId: owner.userId, organisationId: owner.organisationId }));
}

async function readAll(store: DraftStorage, owner?: DraftOwner): Promise<OfflineDraft[]> {
  if (owner) await bindOwner(store, owner);
  const raw = await store.getItem(storageKey(owner));
  if (!raw) return [];
  const parsed = JSON.parse(raw) as { v?: number; ciphertext?: string; userId?: string; organisationId?: string };
  if (owner) {
    if (parsed.userId !== owner.userId || parsed.organisationId !== owner.organisationId) {
      throw new DraftAccountError();
    }
  }
  if (!parsed.ciphertext) throw new Error('Drafts on this device could not be read.');
  const key = await getOrCreateKey(store);
  const plain = decodeText(xorBytes(base64ToBytes(parsed.ciphertext), key));
  const drafts = JSON.parse(plain) as unknown;
  if (!Array.isArray(drafts) || !drafts.every(isDraft)) throw new Error('Drafts on this device could not be read.');
  return drafts.map(normaliseDraft);
}

async function writeAll(store: DraftStorage, drafts: OfflineDraft[], owner?: DraftOwner): Promise<void> {
  const keyName = storageKey(owner);
  if (drafts.length === 0) {
    await store.removeItem(keyName);
    return;
  }
  if (owner) await bindOwner(store, owner);
  const key = await getOrCreateKey(store);
  const ciphertext = bytesToBase64(xorBytes(encodeText(JSON.stringify(drafts)), key));
  const envelope: { v: number; ciphertext: string; userId?: string; organisationId?: string } = { v: 2, ciphertext };
  if (owner) {
    envelope.userId = owner.userId;
    envelope.organisationId = owner.organisationId;
  }
  await store.setItem(keyName, JSON.stringify(envelope));
}

export async function loadDrafts(store?: DraftStorage, owner?: DraftOwner): Promise<OfflineDraft[]> {
  return readAll(resolveStore(store), owner);
}

export async function saveDraft(input: SaveDraftInput, store?: DraftStorage, owner?: DraftOwner): Promise<OfflineDraft> {
  const resolved = resolveStore(store);
  const drafts = await readAll(resolved, owner);
  const payload = stripDraftSecrets(input.payload);
  const key = draftResourceKey(input.type, payload);
  const existing = drafts.find((draft) => draftResourceKey(draft.type, draft.payload) === key);
  const now = new Date().toISOString();
  const next: OfflineDraft = {
    id: existing?.id ?? createId(),
    type: input.type,
    payload,
    clientRequestId: existing?.clientRequestId ?? createId(),
    createdAt: existing?.createdAt ?? now,
    localUpdatedAt: now,
    updatedAt: now,
    localAttachmentUris: input.localAttachmentUris ?? existing?.localAttachmentUris ?? [],
    serverUpdatedAt: input.serverUpdatedAt ?? existing?.serverUpdatedAt,
    serverResourceId: input.serverResourceId ?? existing?.serverResourceId,
    syncState: input.syncState ?? 'pending',
    lastError: input.lastError,
  };
  await writeAll(resolved, [...drafts.filter((draft) => draft.id !== next.id), next], owner);
  return next;
}

export async function clearDraft(id: string, store?: DraftStorage, owner?: DraftOwner): Promise<void> {
  const resolved = resolveStore(store);
  const drafts = await readAll(resolved, owner);
  await writeAll(
    resolved,
    drafts.filter((draft) => draft.id !== id),
    owner,
  );
}

export async function updateDraft(
  id: string,
  patch: Partial<Pick<OfflineDraft, 'syncState' | 'lastError' | 'serverUpdatedAt' | 'serverResourceId' | 'localAttachmentUris' | 'payload'>>,
  store?: DraftStorage,
  owner?: DraftOwner,
): Promise<OfflineDraft | null> {
  const resolved = resolveStore(store);
  const drafts = await readAll(resolved, owner);
  let updated: OfflineDraft | null = null;
  const now = new Date().toISOString();
  const next = drafts.map((draft) => {
    if (draft.id !== id) return draft;
    updated = {
      ...draft,
      ...patch,
      payload: patch.payload ? stripDraftSecrets(patch.payload) : draft.payload,
      localUpdatedAt: now,
      updatedAt: now,
    };
    return updated;
  });
  await writeAll(resolved, next, owner);
  return updated;
}

export async function markDraftError(id: string, error: string, store?: DraftStorage, owner?: DraftOwner): Promise<void> {
  await updateDraft(id, { syncState: 'failed', lastError: error }, store, owner);
}
