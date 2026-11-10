import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useRef, useState } from 'react';

import { useAuth } from '@/contexts/AuthContext';
import {
  loadNetInfo,
  readConnectivity,
  scheduleReconnectSync,
  shouldSyncOnReconnect,
  type Connectivity,
} from '@/lib/hmore/offline/network';
import { submitOfflineDraft, uploadDraftAttachment } from '@/lib/hmore/offline/submit';
import {
  clearDraft,
  DraftAccountError,
  loadDrafts,
  saveDraft,
  type DraftOwner,
  type DraftType,
  type OfflineDraft,
  type SaveDraftInput,
  type SyncState,
} from '@/lib/hmore/offline/store';
import { syncNow, type SyncReport } from '@/lib/hmore/offline/syncEngine';

const DRAFT_KEY = ['hmore', 'offline', 'drafts'] as const;

export function draftOwner(userId?: string | null, organisationId?: string | null): DraftOwner | null {
  if (!userId || !organisationId) return null;
  return { userId, organisationId };
}

export function useOfflineDrafts() {
  const { user, hmore } = useAuth();
  const owner = draftOwner(user?.id, hmore?.rbac.active_organisation_id);
  const client = useQueryClient();
  const query = useQuery({
    queryKey: [...DRAFT_KEY, owner?.userId ?? '', owner?.organisationId ?? ''],
    queryFn: () => (owner ? loadDrafts(undefined, owner) : Promise.resolve([])),
    enabled: !!owner,
  });
  const [syncing, setSyncing] = useState(false);

  const refresh = useCallback(async () => {
    await client.invalidateQueries({ queryKey: DRAFT_KEY });
  }, [client]);

  const run = useCallback(
    async (states?: SyncState[]): Promise<SyncReport> => {
      if (!owner) return { offline: true, results: [] };
      setSyncing(true);
      try {
        const online = (await readConnectivity()) === 'online';
        const report = await syncNow({
          submit: submitOfflineDraft,
          isOnline: async () => online,
          owner,
          upload: uploadDraftAttachment,
          states,
        });
        await refresh();
        return report;
      } finally {
        setSyncing(false);
      }
    },
    [owner, refresh],
  );

  const save = useCallback(
    async (input: SaveDraftInput): Promise<OfflineDraft> => {
      if (!owner) throw new DraftAccountError('Sign in again before saving a draft.');
      const draft = await saveDraft(input, undefined, owner);
      await refresh();
      return draft;
    },
    [owner, refresh],
  );

  const remove = useCallback(
    async (id: string) => {
      if (!owner) return;
      await clearDraft(id, undefined, owner);
      await refresh();
    },
    [owner, refresh],
  );

  return {
    drafts: query.data ?? [],
    count: query.data?.length ?? 0,
    loading: query.isLoading,
    syncing,
    owner,
    save,
    remove,
    sync: () => run(),
    syncNow: () => run(),
    retryFailed: () => run(['failed']),
    refresh,
  };
}

export function useStaffDrafts() {
  return useOfflineDrafts();
}

/** Listens for a reconnect and syncs once. Mount this in one place, not on every screen. */
export function useOfflineReconnect(sync: () => Promise<unknown>) {
  const syncRef = useRef(sync);
  syncRef.current = sync;
  const [connectivity, setConnectivity] = useState<Connectivity | 'checking'>('checking');

  useEffect(() => {
    let previous: Connectivity | null = null;
    let cancel: (() => void) | null = null;
    let stopped = false;
    const net = loadNetInfo();

    async function apply(next: Connectivity) {
      if (stopped) return;
      setConnectivity(next);
      if (shouldSyncOnReconnect(previous, next)) {
        cancel?.();
        cancel = scheduleReconnectSync(() => syncRef.current());
      }
      previous = next;
    }

    void readConnectivity().then((next) => apply(next));
    const unsubscribe = net?.addEventListener?.((state) => {
      void readConnectivity({ netInfo: { fetch: async () => state } }).then((next) => apply(next));
    });
    return () => {
      stopped = true;
      cancel?.();
      unsubscribe?.();
    };
  }, []);

  return connectivity;
}

export type { DraftType };
