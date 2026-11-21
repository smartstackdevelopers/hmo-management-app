"use client";

import { useState } from "react";
import { btnPrimary, inputClass, labelClass } from "@/components/ui/primitives";
import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  documentId: string;
};

export function NewVersionUploadForm({ accessToken, organisationId, role, documentId }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [note, setNote] = useState("");
  const [status, setStatus] = useState<"idle" | "uploading" | "ok" | "err">("idle");
  const [msg, setMsg] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    setStatus("uploading");
    setMsg(null);
    const form = new FormData();
    form.append("file", file);
    form.append("metadata", JSON.stringify({ change_description: note || null }));
    try {
      const res = await fetch(`${API_BASE}/api/v1/documents/${documentId}/versions`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          ...organisationRequestHeaders({ organisationId, role }),
        },
        body: form,
      });
      if (!res.ok) {
        throw new Error("We couldn't upload that version. Please try again.");
      }
      setStatus("ok");
      setMsg(`New version uploaded (v${(await res.json() as { version_number: number }).version_number})`);
      setFile(null);
      setNote("");
    } catch (err) {
      setStatus("err");
      setMsg(err instanceof Error ? err.message : "Upload failed");
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="space-y-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-card">
      <p className="text-base font-semibold text-slate-900">Upload new version</p>
      <div>
        <label htmlFor="version-file" className={labelClass}>
          File
        </label>
        <input id="version-file" type="file" className="mt-1.5 block w-full text-sm text-slate-700" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </div>
      <div>
        <label htmlFor="version-note" className={labelClass}>
          Change description
        </label>
        <input
          id="version-note"
          className={`mt-1.5 ${inputClass}`}
          placeholder="What changed"
          value={note}
          onChange={(e) => setNote(e.target.value)}
        />
      </div>
      <button type="submit" disabled={status === "uploading"} className={btnPrimary}>
        Upload version
      </button>
      {msg ? <p className={`mt-2 ${status === "err" ? "text-red-700" : "text-slate-600"}`}>{msg}</p> : null}
    </form>
  );
}
