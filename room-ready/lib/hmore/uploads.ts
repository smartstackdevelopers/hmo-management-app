/** Matches the API default in `storage_max_upload_bytes` and `storage_allowed_content_types`. */
export const HMORE_MAX_UPLOAD_BYTES = 10 * 1024 * 1024;

export const HMORE_DOCUMENT_CONTENT_TYPES = [
  'application/pdf',
  'image/jpeg',
  'image/png',
  'image/webp',
  'text/plain',
  'application/msword',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
] as const;

export const HMORE_PHOTO_CONTENT_TYPES = ['image/jpeg', 'image/png', 'image/webp'] as const;

export type UploadKind = 'photo' | 'document';

export interface StaffUploadFile {
  name: string;
  mimeType: string;
  size?: number | null;
}

const EXTENSION_TYPES: Record<string, string> = {
  pdf: 'application/pdf',
  jpg: 'image/jpeg',
  jpeg: 'image/jpeg',
  png: 'image/png',
  webp: 'image/webp',
  txt: 'text/plain',
  doc: 'application/msword',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
};

export function mimeFromName(name: string, declared?: string | null): string {
  const declaredType = declared?.split(';')[0]?.trim().toLowerCase();
  if (declaredType && declaredType !== 'application/octet-stream') return declaredType;
  const extension = name.split('.').pop()?.toLowerCase() ?? '';
  return EXTENSION_TYPES[extension] ?? declaredType ?? 'application/octet-stream';
}

/** Returns an error message, or null when the file matches the API allow-list. */
export function validateStaffUpload(file: StaffUploadFile, kind: UploadKind): string | null {
  const mimeType = mimeFromName(file.name, file.mimeType);
  const allowed: readonly string[] = kind === 'photo' ? HMORE_PHOTO_CONTENT_TYPES : HMORE_DOCUMENT_CONTENT_TYPES;
  if (!allowed.includes(mimeType)) {
    return kind === 'photo'
      ? 'Photos must be JPEG, PNG, or WebP.'
      : 'This file type is not accepted. Use a PDF, image, text file, or Word document.';
  }
  if (typeof file.size === 'number' && file.size > HMORE_MAX_UPLOAD_BYTES) {
    return `File exceeds the ${HMORE_MAX_UPLOAD_BYTES} byte limit.`;
  }
  if (file.size === 0) return 'The file is empty.';
  return null;
}
