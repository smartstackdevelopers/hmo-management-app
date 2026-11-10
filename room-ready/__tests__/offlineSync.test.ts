import { DraftAccountError, draftStorageKey, loadDrafts, saveDraft, type DraftStorage } from '@/lib/hmore/offline/store';
import { retainAttachment, type AttachmentFileStore } from '@/lib/hmore/offline/attachments';
import { readConnectivity, shouldSyncOnReconnect } from '@/lib/hmore/offline/network';
import { idempotencyHeaders, syncNow } from '@/lib/hmore/offline/syncEngine';

function memoryStore(): DraftStorage & { secure: Map<string, string>; items: Map<string, string> } {
  const secure = new Map<string, string>();
  const items = new Map<string, string>();
  return {
    secure,
    items,
    getSecure: async (key) => secure.get(key) ?? null,
    setSecure: async (key, value) => {
      if (value.length > 2048) throw new Error('SecureStore value is too large');
      secure.set(key, value);
    },
    getItem: async (key) => items.get(key) ?? null,
    setItem: async (key, value) => {
      items.set(key, value);
    },
    removeItem: async (key) => {
      items.delete(key);
    },
  };
}

const ownerA = { userId: 'user-a', organisationId: 'org-a' };
const ownerB = { userId: 'user-b', organisationId: 'org-b' };

describe('offline sync', () => {
  it('encrypts drafts for one account and refuses another account', async () => {
    const store = memoryStore();
    const notes = 'private welfare note '.repeat(80);
    await saveDraft(
      { type: 'daily_log', payload: { tenant_id: 'tenant-1', notes, summary: 'Check', password: 'must-not-store' } },
      store,
      ownerA,
    );
    const raw = store.items.get(draftStorageKey(ownerA)) ?? '';
    expect(raw).not.toContain(notes);
    expect(raw).not.toContain('must-not-store');
    for (const value of store.secure.values()) expect(value.length).toBeLessThanOrEqual(2048);

    const loaded = await loadDrafts(store, ownerA);
    expect(loaded).toHaveLength(1);
    expect(loaded[0].payload.notes).toBe(notes);
    expect(loaded[0].payload.password).toBeUndefined();

    const copied = raw;
    expect(await loadDrafts(store, ownerB)).toEqual([]);
    await store.setItem(draftStorageKey(ownerB), copied);
    await expect(loadDrafts(store, ownerB)).rejects.toBeInstanceOf(DraftAccountError);
  });

  it('reuses the same clientRequestId when a draft is retried', async () => {
    const store = memoryStore();
    const first = await saveDraft({ type: 'visit_update', payload: { visit_id: 'visit-1', status: 'completed' } }, store, ownerA);
    const replaced = await saveDraft(
      { type: 'visit_update', payload: { visit_id: 'visit-1', status: 'completed', outcome: 'seen' } },
      store,
      ownerA,
    );
    expect(replaced.clientRequestId).toBe(first.clientRequestId);
    const sent: string[] = [];
    await syncNow({
      store,
      owner: ownerA,
      isOnline: async () => true,
      submit: async (draft) => {
        sent.push(draft.clientRequestId);
        return { status: 500, error: 'no' };
      },
    });
    await syncNow({
      store,
      owner: ownerA,
      isOnline: async () => true,
      submit: async (draft) => {
        sent.push(idempotencyHeaders(draft)['Idempotency-Key']);
        return { status: 200, serverResourceId: 'visit-1' };
      },
    });
    expect(sent).toEqual([first.clientRequestId, first.clientRequestId]);
    expect(await loadDrafts(store, ownerA)).toEqual([]);
  });

  it('keeps the local draft and marks a conflict instead of deleting it', async () => {
    const store = memoryStore();
    const saved = await saveDraft(
      { type: 'task_update', payload: { task_id: 'task-1', status: 'completed', note: 'local' } },
      store,
      ownerA,
    );
    const report = await syncNow({
      store,
      owner: ownerA,
      isOnline: async () => true,
      submit: async () => ({ status: 409, error: 'The record changed on the server.', serverUpdatedAt: '2026-11-10T12:00:00+00:00' }),
    });
    expect(report.results[0]).toMatchObject({ id: saved.id, saved: false, status: 409, syncState: 'conflict' });
    const [draft] = await loadDrafts(store, ownerA);
    expect(draft.syncState).toBe('conflict');
    expect(draft.payload.note).toBe('local');
    expect(draft.serverUpdatedAt).toBe('2026-11-10T12:00:00+00:00');
    expect(draft.lastError).toContain('changed');
  });

  it('deletes a local photo only after the upload succeeds', async () => {
    const store = memoryStore();
    const removed: string[] = [];
    const files: AttachmentFileStore = {
      documentDirectory: 'file:///docs/',
      copyAsync: async () => undefined,
      deleteAsync: async (uri) => {
        removed.push(uri);
      },
      makeDirectoryAsync: async () => undefined,
    };
    const uri = await retainAttachment(ownerA, 'file:///tmp/leak.jpg', 'repair-1', files, 'leak.jpg');
    expect(uri).toContain('org-a');
    expect(uri).toContain('user-a');
    await saveDraft(
      {
        type: 'repair_create',
        payload: { property_id: 'property-1', title: 'Leak', description: 'Kitchen', local_files: [{ uri, name: 'leak.jpg', mimeType: 'image/jpeg' }] },
        localAttachmentUris: [uri],
      },
      store,
      ownerA,
    );
    await syncNow({
      store,
      owner: ownerA,
      isOnline: async () => true,
      submit: async () => ({ status: 201, serverResourceId: 'repair-1' }),
      upload: async () => {
        throw new Error('upload failed');
      },
      release: async (fileUri) => {
        removed.push(fileUri);
      },
    });
    expect(removed).toEqual([]);
    expect((await loadDrafts(store, ownerA))[0].localAttachmentUris).toEqual([uri]);

    await syncNow({
      store,
      owner: ownerA,
      isOnline: async () => true,
      submit: async () => ({ status: 201, serverResourceId: 'repair-1' }),
      upload: async () => undefined,
      release: async (fileUri) => {
        removed.push(fileUri);
      },
    });
    expect(removed).toEqual([uri]);
    expect(await loadDrafts(store, ownerA)).toEqual([]);
  });

  it('reports offline, unstable, and online without treating a dead API as online', async () => {
    await expect(
      readConnectivity({ netInfo: { fetch: async () => ({ isConnected: false }) }, ping: async () => true }),
    ).resolves.toBe('offline');
    await expect(
      readConnectivity({ netInfo: { fetch: async () => ({ isConnected: true }) }, ping: async () => false }),
    ).resolves.toBe('unstable');
    await expect(
      readConnectivity({ netInfo: { fetch: async () => ({ isConnected: true }) }, ping: async () => true }),
    ).resolves.toBe('online');
    expect(shouldSyncOnReconnect('offline', 'online')).toBe(true);
    expect(shouldSyncOnReconnect('unstable', 'online')).toBe(true);
    expect(shouldSyncOnReconnect(null, 'online')).toBe(false);
    expect(shouldSyncOnReconnect('online', 'online')).toBe(false);
  });
});
