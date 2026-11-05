"use client";

import { useState, type ChangeEvent } from "react";

import { uploadPrivateFile, type FileMeta } from "@/lib/filesApi";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string;
  onUploaded?: (meta: FileMeta) => void;
};

/**
 * Minimal authenticated private upload control. Does not talk to object storage
 * directly and never embeds credentials.
 */
export function PrivateFileUpload({
  accessToken,
  organisationId,
  role,
  onUploaded,
}: Props) {
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [last, setLast] = useState<FileMeta | null>(null);

  async function onChange(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    setError(null);
    setProgress(0);
    try {
      const meta = await uploadPrivateFile({
        accessToken,
        organisationId,
        role,
        file,
        onProgress: setProgress,
      });
      setLast(meta);
      onUploaded?.(meta);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setProgress(null);
      event.target.value = "";
    }
  }

  return (
    <div className="space-y-2 text-sm text-slate-700">
      <label className="block font-medium text-slate-900">
        Private file upload
        <input
          type="file"
          className="mt-1 block w-full text-sm"
          onChange={onChange}
          disabled={progress !== null}
        />
      </label>
      {progress !== null ? (
        <p>Uploading… {Math.round(progress * 100)}%</p>
      ) : null}
      {error ? <p className="text-red-700">{error}</p> : null}
      {last ? (
        <p>
          Saved <span className="font-mono">{last.original_filename}</span> (
          {last.id})
        </p>
      ) : null}
    </div>
  );
}
