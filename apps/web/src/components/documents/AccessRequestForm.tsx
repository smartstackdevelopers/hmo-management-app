"use client";

import { useState } from "react";
import { createAccessRequest } from "@/lib/managedDocumentsApi";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  documentId: string;
};

export function AccessRequestForm(props: Props) {
  const [reason, setReason] = useState("");
  const [status, setStatus] = useState<"idle" | "sending" | "ok" | "err">("idle");
  const [msg, setMsg] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!reason.trim()) return;
    setStatus("sending");
    setMsg(null);
    try {
      await createAccessRequest({
        ...props,
        body: { reason: reason.trim() },
      });
      setStatus("ok");
      setMsg("Request submitted. A reviewer must approve before access changes.");
      setReason("");
    } catch (err) {
      setStatus("err");
      setMsg(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="rounded border border-slate-200 bg-slate-50 p-4 text-sm">
      <p className="font-medium text-slate-800">Request access</p>
      <textarea
        className="mt-2 w-full rounded border border-slate-300 px-2 py-1"
        rows={3}
        value={reason}
        onChange={(e) => setReason(e.target.value)}
        placeholder="Reason for access"
      />
      <button
        type="submit"
        disabled={status === "sending"}
        className="mt-2 rounded bg-slate-800 px-3 py-1 text-white disabled:opacity-50"
      >
        Submit request
      </button>
      {msg ? <p className={`mt-2 ${status === "err" ? "text-red-700" : "text-slate-600"}`}>{msg}</p> : null}
    </form>
  );
}
