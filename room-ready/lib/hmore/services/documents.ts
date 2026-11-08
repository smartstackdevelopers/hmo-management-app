import { HmoreApiError, hmoreFetch, hmoreRequestResponse } from '@/lib/hmore/client';
import type { ManagedDocument, Page } from '@/lib/hmore/types';

export function listDocuments(): Promise<Page<ManagedDocument>> {
  return hmoreFetch<Page<ManagedDocument>>('/documents', {
    method: 'GET',
    query: { page: 1, page_size: 50 },
  });
}

export function getDocument(id: string): Promise<ManagedDocument> {
  return hmoreFetch<ManagedDocument>(`/documents/${id}`, { method: 'GET' });
}

export async function fetchDocumentContent(id: string): Promise<{ bytes: ArrayBuffer; contentType: string }> {
  const response = await hmoreRequestResponse(`/documents/${id}/content`, { method: 'GET' });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    const detail =
      data && typeof data === 'object' && typeof (data as { detail?: unknown }).detail === 'string'
        ? (data as { detail: string }).detail
        : 'Could not open this file';
    throw new HmoreApiError(response.status, detail);
  }
  const bytes = await response.arrayBuffer();
  const contentType = response.headers.get('content-type') ?? 'application/octet-stream';
  return { bytes, contentType };
}
