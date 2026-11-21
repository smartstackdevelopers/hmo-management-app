"use client";

import { useState } from "react";
import { btnPrimary, inputClass, labelClass } from "@/components/ui/primitives";
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
    } catch {
      setStatus("err");
      setMsg("We couldn't record that acknowledgement. Please try again.");
    }
  }

  return (
    <form onSubmit={(e) => void submit(e)} className="space-y-3 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-sm">
      <p className="font-semibold text-amber-950">Complete signature (internal record)</p>
      <p className="text-xs leading-5 text-amber-900">
        This is not a qualified electronic signature under eIDAS or similar regimes. External trust services are a
        documented integration boundary for a future provider.
      </p>
      <div>
        <label className={labelClass} htmlFor="signature-consent">
          Consent text
        </label>
        <textarea
          id="signature-consent"
          className={`mt-1.5 ${inputClass} h-auto py-2`}
          rows={2}
          value={consent}
          onChange={(e) => setConsent(e.target.value)}
        />
      </div>
      <p className="text-xs text-slate-600">
        Required phrase: <code className="rounded bg-white px-1">{ACK}</code>
      </p>
      <button type="submit" disabled={status === "sending"} className={btnPrimary}>
        Record acknowledgement
      </button>
      {msg ? <p className={status === "err" ? "text-red-700" : "text-slate-700"}>{msg}</p> : null}
    </form>
  );
}
