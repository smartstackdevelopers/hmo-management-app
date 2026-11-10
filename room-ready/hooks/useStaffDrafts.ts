import { useQuery, useQueryClient } from '@tanstack/react-query';

import { isDeviceOnline, pingHmoreHealth } from '@/lib/hmore/staff/network';
import {
  clearDraft,
  loadDrafts,
  saveDraft,
  syncDrafts,
  type DraftType,
  type StaffDraft,
} from '@/lib/hmore/staff/offlineDrafts';
import { submitStaffDraft } from '@/lib/hmore/staff/syncDraft';

const DRAFT_KEY = ['hmore', 'staff', 'drafts'] as const;

export function useStaffDrafts() {
  const client = useQueryClient();
  const query = useQuery({ queryKey: DRAFT_KEY, queryFn: () => loadDrafts() });

  async function refresh() {
    await client.invalidateQueries({ queryKey: DRAFT_KEY });
  }

  async function save(input: { type: DraftType; payload: Record<string, unknown> }): Promise<StaffDraft> {
    const draft = await saveDraft(input);
    await refresh();
    return draft;
  }

  async function remove(id: string) {
    await clearDraft(id);
    await refresh();
  }

  async function sync() {
    const online = await isDeviceOnline({ ping: pingHmoreHealth });
    const report = await syncDrafts(submitStaffDraft, async () => online);
    await refresh();
    return report;
  }

  return {
    drafts: query.data ?? [],
    count: query.data?.length ?? 0,
    loading: query.isLoading,
    save,
    remove,
    sync,
    refresh,
  };
}
