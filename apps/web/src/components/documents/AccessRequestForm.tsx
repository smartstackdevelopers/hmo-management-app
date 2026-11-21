"use client";

import { useState } from "react";
import { btnPrimary, inputClass, labelClass } from "@/components/ui/primitives";
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
    } catch {
      setStatus("err");
      setMsg("We couldn't submit that request. Please try again.");
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="space-y-3 rounded-2xl border border-slate-200 bg-white p-6 text-sm shadow-card">
      <p className="text-base font-semibold text-slate-900">Request access</p>
      <div>
        <label htmlFor="access-reason" className={labelClass}>
          Reason for access
        </label>
        <textarea
          id="access-reason"
          className={`mt-1.5 ${inputClass} h-auto py-2`}
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Why you need access"
        />
      </div>
      <button
        type="submit"
        disabled={status === "sending"}
        className={btnPrimary}
      >
        Submit request
      </button>
      {msg ? <p className={`mt-2 ${status === "err" ? "text-red-700" : "text-slate-600"}`}>{msg}</p> : null}
    </form>
  );
}
