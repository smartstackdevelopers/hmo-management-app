"use client";

import { btnPrimary } from "@/components/ui/primitives";
import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type SecureDocumentDownloadProps = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  documentId: string;
  label?: string;
};

/** Browser download via authenticated API (no storage URL exposure). */
export function SecureDocumentDownload({
  accessToken,
  organisationId,
  role,
  documentId,
  label = "Download current version",
}: SecureDocumentDownloadProps) {
  async function onClick() {
    const headers: Record<string, string> = {
      Authorization: `Bearer ${accessToken}`,
      ...organisationRequestHeaders({ organisationId, role }),
    };
    const res = await fetch(`${API_BASE}/api/v1/documents/${documentId}/content`, {
      headers,
      cache: "no-store",
    });
    if (!res.ok) {
      alert("We couldn't download this file. Please try again.");
      return;
    }
    const blob = await res.blob();
    const cd = res.headers.get("Content-Disposition");
    let filename = "document";
    const m = cd?.match(/filename\\*=UTF-8''([^;]+)/);
    if (m?.[1]) {
      filename = decodeURIComponent(m[1]);
    }
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <button
      type="button"
      onClick={() => void onClick()}
      className={btnPrimary}
    >
      {label}
    </button>
  );
}
