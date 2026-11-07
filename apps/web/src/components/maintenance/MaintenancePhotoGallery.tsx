"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { organisationRequestHeaders } from "@/lib/organisation";
import type { RequestFileLink } from "@/lib/maintenanceApi";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export function MaintenancePhotoGallery({
  requestId,
  files,
  accessToken,
  organisationId,
  role,
}: {
  requestId: string;
  files: RequestFileLink[];
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  const [urls, setUrls] = useState<Record<string, string>>({});
  const [errors, setErrors] = useState<Record<string, string>>({});
  const blobUrlsRef = useRef<string[]>([]);

  const fileIdKey = useMemo(
    () =>
      files
        .map((f) => f.file_id)
        .sort()
        .join(","),
    [files],
  );

  useEffect(() => {
    blobUrlsRef.current.forEach((u) => URL.revokeObjectURL(u));
    blobUrlsRef.current = [];
    let cancelled = false;

    async function load() {
      const next: Record<string, string> = {};
      const nextErr: Record<string, string> = {};
      for (const f of files) {
        try {
          const path = `/api/v1/maintenance/${requestId}/files/${f.file_id}/content`;
          const res = await fetch(`${API_BASE}${path}`, {
            headers: {
              Authorization: `Bearer ${accessToken}`,
              ...organisationRequestHeaders({ organisationId, role }),
            },
            cache: "no-store",
          });
          if (!res.ok) {
            nextErr[f.file_id] = `Could not load image (${res.status})`;
            continue;
          }
          const blob = await res.blob();
          const url = URL.createObjectURL(blob);
          blobUrlsRef.current.push(url);
          next[f.file_id] = url;
        } catch {
          nextErr[f.file_id] = "Could not load image";
        }
      }
      if (!cancelled) {
        setUrls(next);
        setErrors(nextErr);
      }
    }

    void load();

    return () => {
      cancelled = true;
      blobUrlsRef.current.forEach((u) => URL.revokeObjectURL(u));
      blobUrlsRef.current = [];
    };
  }, [requestId, accessToken, organisationId, role, fileIdKey, files]);

  if (files.length === 0) {
    return <p className="text-sm text-slate-500">No photographs yet.</p>;
  }

  return (
    <ul className="grid gap-3 sm:grid-cols-2">
      {files.map((f) => (
        <li key={f.file_id} className="rounded border border-slate-200 p-2">
          {urls[f.file_id] ? (
            // eslint-disable-next-line @next/next/no-img-element -- private blob from authorised API
            <img src={urls[f.file_id]} alt={f.caption || "Maintenance photo"} className="h-40 w-full rounded object-cover" />
          ) : errors[f.file_id] ? (
            <p className="text-xs text-red-700">{errors[f.file_id]}</p>
          ) : (
            <p className="text-xs text-slate-500">Loading…</p>
          )}
          <p className="mt-1 text-xs uppercase text-slate-500">{f.photo_kind}</p>
          {f.caption ? <p className="text-sm text-slate-800">{f.caption}</p> : null}
          <p className="mt-1 font-mono text-[10px] text-slate-400">{f.file_id}</p>
        </li>
      ))}
    </ul>
  );
}
