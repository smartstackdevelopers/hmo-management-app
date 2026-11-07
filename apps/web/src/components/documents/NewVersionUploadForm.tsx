"use client";

import { useState } from "react";
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
        const text = await res.text();
        throw new Error(text || `Failed (${res.status})`);
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
    <form onSubmit={(e) => void submit(e)} className="rounded border border-dashed border-slate-300 p-4 text-sm">
      <p className="font-medium">Upload new version</p>
      <input type="file" className="mt-2 block w-full text-sm" onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      <input
        className="mt-2 w-full rounded border px-2 py-1"
        placeholder="Change description"
        value={note}
        onChange={(e) => setNote(e.target.value)}
      />
      <button type="submit" disabled={status === "uploading"} className="mt-2 rounded bg-teal-700 px-3 py-1 text-white">
        Upload version
      </button>
      {msg ? <p className={`mt-2 ${status === "err" ? "text-red-700" : "text-slate-600"}`}>{msg}</p> : null}
    </form>
  );
}
