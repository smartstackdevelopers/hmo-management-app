"use client";

import { useState } from "react";
import { completeSignatureRequest } from "@/lib/managedDocumentsApi";

const ACK =
  "I acknowledge this in-platform record is not a qualified electronic signature.";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  signatureId: string;
};

export function SignatureCompleteForm(props: Props) {
  const [consent, setConsent] = useState("I consent to record my acknowledgement in HMore.");
  const [status, setStatus] = useState<"idle" | "sending" | "ok" | "err">("idle");
  const [msg, setMsg] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setStatus("sending");
    setMsg(null);
    try {
      await completeSignatureRequest({
        ...props,
        body: { consent_text: consent, acknowledgement: ACK },
      });
      setStatus("ok");
      setMsg("Signature recorded as an in-platform acknowledgement only.");
    } catch (err) {
      setStatus("err");
      setMsg(err instanceof Error ? err.message : "Failed");
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="space-y-2 rounded border border-amber-200 bg-amber-50 p-3 text-sm">
      <p className="font-medium text-amber-900">Complete signature (internal record)</p>
      <p className="text-xs text-amber-900/90">
        This is not a qualified electronic signature under eIDAS or similar regimes. External trust services are a
        documented integration boundary for a future provider.
      </p>
      <label className="block text-xs text-slate-700">Consent text</label>
      <textarea className="w-full rounded border px-2 py-1" rows={2} value={consent} onChange={(e) => setConsent(e.target.value)} />
      <p className="text-xs text-slate-600">
        Required phrase: <code className="rounded bg-white px-1">{ACK}</code>
      </p>
      <button type="submit" disabled={status === "sending"} className="rounded bg-forest-900 px-3 py-1 text-white">
        Record acknowledgement
      </button>
      {msg ? <p className={status === "err" ? "text-red-700" : "text-slate-700"}>{msg}</p> : null}
    </form>
  );
}
