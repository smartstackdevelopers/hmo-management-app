export { readConnectivity, scheduleReconnectSync, shouldSyncOnReconnect } from '@/lib/hmore/offline/network';
export { retainAttachment, releaseAttachment } from '@/lib/hmore/offline/attachments';
export { submitOfflineDraft, uploadDraftAttachment } from '@/lib/hmore/offline/submit';
export { idempotencyHeaders, syncDrafts, syncNow } from '@/lib/hmore/offline/syncEngine';
export type { SyncAck, SyncReport, SyncResultItem } from '@/lib/hmore/offline/syncEngine';
export {
  DraftAccountError,
  draftStorageKey,
  loadDrafts,
  saveDraft,
  sameOwner,
  stripDraftSecrets,
} from '@/lib/hmore/offline/store';
export type { DraftOwner, DraftStorage, DraftType, OfflineDraft, SyncState } from '@/lib/hmore/offline/store';
