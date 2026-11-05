/**
 * F1.8 private file API client. Browser never receives storage credentials or keys.
 */

import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export type FileMeta = {
  id: string;
  organisation_id: string;
  original_filename: string;
  content_type: string;
  size_bytes: number;
  status: string;
  checksum_sha256?: string | null;
  resource_type?: string | null;
  resource_id?: string | null;
};

export async function uploadPrivateFile(options: {
  accessToken: string;
  organisationId: string;
  role?: string;
  file: File;
  resourceType?: string;
  resourceId?: string;
  onProgress?: (ratio: number) => void;
}): Promise<FileMeta> {
  const form = new FormData();
  form.append("upload", options.file);
  if (options.resourceType) {
    form.append("resource_type", options.resourceType);
  }
  if (options.resourceId) {
    form.append("resource_id", options.resourceId);
  }

  // XMLHttpRequest allows upload progress without exposing storage endpoints.
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_BASE}/api/v1/files`);
    xhr.setRequestHeader("Authorization", `Bearer ${options.accessToken}`);
    const orgHeaders = organisationRequestHeaders({
      organisationId: options.organisationId,
      role: options.role,
    });
    for (const [key, value] of Object.entries(orgHeaders)) {
      xhr.setRequestHeader(key, value);
    }
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && options.onProgress) {
        options.onProgress(event.loaded / event.total);
      }
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText) as FileMeta);
        return;
      }
      reject(new Error(xhr.responseText || `Upload failed (${xhr.status})`));
    };
    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.send(form);
  });
}

export function privateFileContentUrl(fileId: string): string {
  return `${API_BASE}/api/v1/files/${fileId}/content`;
}
