"use client";

import { useState } from "react";
import { organisationRequestHeaders } from "@/lib/organisation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type CategoryOption = { id: string; code: string; title: string };

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  categories: CategoryOption[];
};

export function DocumentUploadForm({ accessToken, organisationId, role, categories }: Props) {
  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState(categories[0]?.id ?? "");
  const [file, setFile] = useState<File | null>(null);
  const [status, setStatus] = useState<"idle" | "uploading" | "done" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || !categoryId || !title.trim()) {
      setMessage("Title, category, and file are required.");
      setStatus("error");
      return;
    }
    setStatus("uploading");
    setMessage(null);
    const metadata = JSON.stringify({
      title: title.trim(),
      category_id: categoryId,
      access_classification: "standard",
      links: [],
    });
    const form = new FormData();
    form.append("metadata", metadata);
    form.append("file", file);
    try {
      const res = await fetch(`${API_BASE}/api/v1/documents`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${accessToken}`,
          ...organisationRequestHeaders({ organisationId, role }),
        },
        body: form,
      });
      if (!res.ok) {
        const text = await res.text();
        throw new Error(text || `Upload failed (${res.status})`);
      }
      await res.json();
      setStatus("done");
      setMessage("Upload completed. Open the document list to verify.");
      setTitle("");
      setFile(null);
    } catch (err) {
      setStatus("error");
      setMessage(err instanceof Error ? err.message : "Upload failed");
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="space-y-4 rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
      <div>
        <label className="block text-sm font-medium text-slate-700" htmlFor="doc-title">
          Title
        </label>
        <input
          id="doc-title"
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700" htmlFor="doc-cat">
          Category
        </label>
        <select
          id="doc-cat"
          className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm"
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
        >
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.title} ({c.code})
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium text-slate-700" htmlFor="doc-file">
          File
        </label>
        <input
          id="doc-file"
          type="file"
          className="mt-1 w-full text-sm"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </div>
      <button
        type="submit"
        disabled={status === "uploading"}
        className="rounded-md bg-forest-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
      >
        {status === "uploading" ? "Uploading…" : "Upload"}
      </button>
      {message ? (
        <p className={`text-sm ${status === "error" ? "text-red-700" : "text-slate-600"}`}>{message}</p>
      ) : null}
    </form>
  );
}
