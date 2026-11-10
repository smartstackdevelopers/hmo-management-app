import type { AttachmentFileStore } from '@/lib/hmore/offline/attachments';
import { releaseAttachment } from '@/lib/hmore/offline/attachments';
import type { DraftOwner, DraftStorage, OfflineDraft, SyncState } from '@/lib/hmore/offline/store';
import { clearDraft, loadDrafts, updateDraft } from '@/lib/hmore/offline/store';
import { deviceSessionAllowsSync } from '@/lib/hmore/security/deviceSessionGate';

export interface SyncAck {
  status: number;
  error?: string;
  serverUpdatedAt?: string;
  serverResourceId?: string;
}

export interface SyncResultItem {
  id: string;
  saved: boolean;
  status: number;
  error?: string;
  syncState: SyncState;
  serverResourceId?: string;
}

export interface SyncReport {
  offline: boolean;
  results: SyncResultItem[];
  blockedReason?: 'device_session_revoked';
}

export interface SyncNowOptions {
  submit: (draft: OfflineDraft) => Promise<SyncAck>;
  isOnline: () => Promise<boolean>;
  store?: DraftStorage;
  owner?: DraftOwner;
  upload?: (draft: OfflineDraft, uri: string, resourceId: string) => Promise<void>;
  release?: (uri: string) => Promise<void>;
  files?: AttachmentFileStore;
  /** Defaults to drafts that can be retried. Conflict and needs-attention stay for the user. */
  states?: SyncState[];
  /** When omitted, sync checks the stored device-session status and skips a revoked device. */
  deviceSessionAllowsSync?: () => Promise<boolean>;
}

const RETRY_STATES: SyncState[] = ['draft', 'pending', 'failed', 'syncing'];
const locks = new WeakMap<DraftStorage, Promise<unknown>>();

export function idempotencyHeaders(draft: Pick<OfflineDraft, 'clientRequestId'>): Record<string, string> {
  return { 'Idempotency-Key': draft.clientRequestId };
}

function confirmed(status: number): boolean {
  return status >= 200 && status < 300;
}

function stateForFailure(status: number): SyncState {
  if (status === 409) return 'conflict';
  if (status === 0 || status >= 500) return 'failed';
  return 'needs_attention';
}

async function withLock<T>(store: DraftStorage, run: () => Promise<T>): Promise<T> {
  const previous = locks.get(store) ?? Promise.resolve();
  let release: () => void = () => undefined;
  const gate = new Promise<void>((resolve) => {
    release = () => resolve();
  });
  const tail = previous.then(() => gate);
  locks.set(store, tail);
  await previous;
  try {
    return await run();
  } finally {
    release();
  }
}

/**
 * Sends drafts one at a time. A draft is removed only after a 2xx response and,
 * when it has photos, after each photo upload also returns success.
 * This is not a continuous background sync. Call it from Sync Now or after reconnect.
 */
export async function syncNow(options: SyncNowOptions): Promise<SyncReport> {
  const allows = options.deviceSessionAllowsSync ?? deviceSessionAllowsSync;
  if (!(await allows())) {
    return { offline: false, results: [], blockedReason: 'device_session_revoked' };
  }
  if (!(await options.isOnline())) return { offline: true, results: [] };
  const store = options.store;
  if (!store) {
    const { createDefaultDraftStorage } = await import('@/lib/hmore/offline/store');
    return syncNow({ ...options, store: createDefaultDraftStorage() });
  }
  return withLock(store, () => runQueue({ ...options, store }));
}

async function runQueue(options: SyncNowOptions & { store: DraftStorage }): Promise<SyncReport> {
  const allowed = new Set(options.states ?? RETRY_STATES);
  const drafts = await loadDrafts(options.store, options.owner);
  const results: SyncResultItem[] = [];
  for (const original of drafts) {
    if (!allowed.has(original.syncState)) continue;
    const current = (await loadDrafts(options.store, options.owner)).find((item) => item.id === original.id) ?? original;
    if (!allowed.has(current.syncState) && current.syncState !== 'syncing') continue;
    await updateDraft(current.id, { syncState: 'syncing', lastError: undefined }, options.store, options.owner);
    try {
      const response = await options.submit(current);
      if (!confirmed(response.status)) {
        const syncState = stateForFailure(response.status);
        const error = response.error || (syncState === 'conflict' ? 'The server copy changed.' : `Not saved (${response.status})`);
        await updateDraft(
          current.id,
          { syncState, lastError: error, serverUpdatedAt: response.serverUpdatedAt ?? current.serverUpdatedAt },
          options.store,
          options.owner,
        );
        results.push({ id: current.id, saved: false, status: response.status, error, syncState });
        continue;
      }
      const resourceId = response.serverResourceId || current.serverResourceId;
      let remaining = [...current.localAttachmentUris];
      if (remaining.length > 0) {
        if (!resourceId || !options.upload) {
          await updateDraft(
            current.id,
            {
              syncState: 'needs_attention',
              serverResourceId: resourceId,
              lastError: 'The record was saved. Photos are still on this device.',
            },
            options.store,
            options.owner,
          );
          results.push({
            id: current.id,
            saved: false,
            status: response.status,
            error: 'The record was saved. Photos are still on this device.',
            syncState: 'needs_attention',
          });
          continue;
        }
        let uploadError: string | null = null;
        for (const uri of [...remaining]) {
          try {
            await options.upload({ ...current, serverResourceId: resourceId }, uri, resourceId);
            const release = options.release ?? ((fileUri: string) => releaseAttachment(fileUri, options.files));
            await release(uri);
            remaining = remaining.filter((item) => item !== uri);
            await updateDraft(
              current.id,
              { localAttachmentUris: remaining, serverResourceId: resourceId, syncState: 'syncing' },
              options.store,
              options.owner,
            );
          } catch (error) {
            uploadError = error instanceof Error ? error.message : 'The photo was not uploaded. It is still on this device.';
            break;
          }
        }
        if (uploadError || remaining.length > 0) {
          await updateDraft(
            current.id,
            {
              syncState: 'failed',
              serverResourceId: resourceId,
              localAttachmentUris: remaining,
              lastError: uploadError || 'A photo is still on this device.',
            },
            options.store,
            options.owner,
          );
          results.push({
            id: current.id,
            saved: false,
            status: response.status,
            error: uploadError || 'A photo is still on this device.',
            syncState: 'failed',
          });
          continue;
        }
      }
      await updateDraft(current.id, { syncState: 'synced', serverResourceId: resourceId, lastError: undefined }, options.store, options.owner);
      await clearDraft(current.id, options.store, options.owner);
      results.push({ id: current.id, saved: true, status: response.status, syncState: 'synced', serverResourceId: resourceId });
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Could not reach HMore. The draft is still on this device.';
      await updateDraft(current.id, { syncState: 'failed', lastError: message }, options.store, options.owner);
      results.push({ id: current.id, saved: false, status: 0, error: message, syncState: 'failed' });
    }
  }
  return { offline: false, results };
}

export async function syncDrafts(
  submit: (draft: OfflineDraft) => Promise<SyncAck>,
  isOnline: () => Promise<boolean>,
  store?: DraftStorage,
  owner?: DraftOwner,
): Promise<SyncReport> {
  return syncNow({ submit, isOnline, store, owner });
}
