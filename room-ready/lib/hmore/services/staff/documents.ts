import { hmoreFetch } from '@/lib/hmore/client';
import { validateStaffUpload, type StaffUploadFile } from '@/lib/hmore/uploads';

export interface DocumentCategory {
  id: string;
  code: string;
  title: string;
  is_active?: boolean;
}

export function listDocumentCategories(): Promise<DocumentCategory[]> {
  return hmoreFetch<DocumentCategory[]>('/documents/categories', { method: 'GET' });
}

export async function uploadLinkedDocument(input: {
  categoryId: string;
  title: string;
  description: string;
  linkType: 'other' | 'tenant' | 'maintenance';
  linkId: string;
  file: { uri: string; name: string; mimeType: string; size?: number | null };
}): Promise<{ id?: string }> {
  const file: StaffUploadFile = { name: input.file.name, mimeType: input.file.mimeType, size: input.file.size };
  const problem = validateStaffUpload(file, 'document');
  if (problem) throw new Error(problem);
  const formData = new FormData();
  formData.append('file', { uri: input.file.uri, name: input.file.name, type: input.file.mimeType } as unknown as Blob);
  formData.append(
    'metadata',
    JSON.stringify({
      title: input.title,
      description: input.description,
      category_id: input.categoryId,
      links: [{ link_type: input.linkType, link_id: input.linkId, label: input.linkType }],
    }),
  );
  return hmoreFetch<{ id?: string }>('/documents', { method: 'POST', formData });
}
