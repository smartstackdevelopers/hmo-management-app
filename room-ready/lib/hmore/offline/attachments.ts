import type { DraftOwner } from '@/lib/hmore/offline/store';

export interface AttachmentFileStore {
  documentDirectory: string | null;
  copyAsync: (from: string, to: string) => Promise<void>;
  deleteAsync: (uri: string) => Promise<void>;
  makeDirectoryAsync: (uri: string) => Promise<void>;
}

type NativeFileSystem = {
  documentDirectory?: string | null;
  copyAsync?: (options: { from: string; to: string }) => Promise<void>;
  deleteAsync?: (uri: string, options?: { idempotent?: boolean }) => Promise<void>;
  makeDirectoryAsync?: (uri: string, options?: { intermediates?: boolean }) => Promise<void>;
};

function loadNativeFileSystem(): AttachmentFileStore {
  let loaded: NativeFileSystem | { default?: NativeFileSystem } | null = null;
  try {
    loaded = require('expo-file-system/legacy') as NativeFileSystem;
  } catch {
    try {
      loaded = require('expo-file-system') as NativeFileSystem | { default?: NativeFileSystem };
    } catch {
      loaded = null;
    }
  }
  const resolved = (loaded && 'default' in loaded && loaded.default ? loaded.default : loaded) as NativeFileSystem | null;
  if (!resolved?.documentDirectory || !resolved.copyAsync || !resolved.makeDirectoryAsync) {
    throw new Error('Photo storage is not available on this device.');
  }
  return {
    documentDirectory: resolved.documentDirectory,
    copyAsync: async (from, to) => {
      await resolved.copyAsync?.({ from, to });
    },
    deleteAsync: async (uri) => {
      await resolved.deleteAsync?.(uri, { idempotent: true });
    },
    makeDirectoryAsync: async (uri) => {
      await resolved.makeDirectoryAsync?.(uri, { intermediates: true });
    },
  };
}

function safeSegment(value: string): string {
  const cleaned = value.replace(/[^a-zA-Z0-9_-]/g, '');
  return cleaned || 'unknown';
}

function fileName(sourceUri: string, preferred?: string): string {
  const raw = preferred || sourceUri.split('/').pop() || 'photo.jpg';
  const cleaned = raw.replace(/[^a-zA-Z0-9._-]/g, '');
  return cleaned || 'photo.jpg';
}

export function attachmentDirectory(owner: DraftOwner, draftKey: string, files: AttachmentFileStore): string {
  const root = files.documentDirectory;
  if (!root) throw new Error('Photo storage is not available on this device.');
  const base = root.endsWith('/') ? root : `${root}/`;
  return `${base}hmore-offline/${safeSegment(owner.organisationId)}/${safeSegment(owner.userId)}/${safeSegment(draftKey)}/`;
}

/** Copy a photo into the app documents folder. The source is left in place. */
export async function retainAttachment(
  owner: DraftOwner,
  sourceUri: string,
  draftKey: string,
  files?: AttachmentFileStore,
  preferredName?: string,
): Promise<string> {
  const store = files ?? loadNativeFileSystem();
  const directory = attachmentDirectory(owner, draftKey, store);
  await store.makeDirectoryAsync(directory);
  const destination = `${directory}${Date.now().toString(16)}-${fileName(sourceUri, preferredName)}`;
  if (sourceUri.startsWith(directory)) return sourceUri;
  await store.copyAsync(sourceUri, destination);
  return destination;
}

/** Delete a retained file only after the server has accepted the upload. */
export async function releaseAttachment(uri: string, files?: AttachmentFileStore): Promise<void> {
  const store = files ?? loadNativeFileSystem();
  await store.deleteAsync(uri);
}
