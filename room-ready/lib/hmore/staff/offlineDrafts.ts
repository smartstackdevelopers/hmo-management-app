export {
  DraftAccountError,
  clearDraft,
  createDefaultDraftStorage,
  draftResourceKey,
  loadDrafts,
  markDraftError,
  saveDraft,
  stripDraftSecrets,
  updateDraft,
  type DraftOwner,
  type DraftStorage,
  type DraftType,
  type OfflineDraft,
  type SaveDraftInput,
  type SyncState,
} from '@/lib/hmore/offline/store';
export { syncDrafts, syncNow, type SyncReport, type SyncResultItem } from '@/lib/hmore/offline/syncEngine';

/** Earlier staff screens use this name for the same draft record. */
export type { OfflineDraft as StaffDraft } from '@/lib/hmore/offline/store';
