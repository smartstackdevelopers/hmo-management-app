"use client";

import { useState } from "react";
import { saveEmploymentSupportNotes } from "@/lib/employmentApi";

export function StaffNotesForm(props: {
  tenantId: string;
  organisationId: string;
  role?: string | null;
  accessToken: string;
  initialNotes: string;
}) {
  const [notes, setNotes] = useState(props.initialNotes);
  const [status, setStatus] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function onSave() {
    setSaving(true);
    setStatus(null);
    try {
      await saveEmploymentSupportNotes({
        accessToken: props.accessToken,
        tenantId: props.tenantId,
        organisationId: props.organisationId,
        role: props.role,
        notes,
      });
      setStatus("Support notes saved.");
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Save failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
      <h2 className="text-sm font-semibold text-slate-900">Support notes</h2>
      <p className="text-sm text-slate-600">
        Permitted employment support notes only. Do not paste private CV content or contact details
        unless policy allows.
      </p>
      <textarea
        className="min-h-28 w-full rounded border border-slate-300 p-3 text-sm"
        value={notes}
        onChange={(event) => setNotes(event.target.value)}
      />
      <button
        type="button"
        disabled={saving || !notes.trim()}
        onClick={() => void onSave()}
        className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
      >
        {saving ? "Saving…" : "Save notes"}
      </button>
      {status ? <p className="text-sm text-slate-600">{status}</p> : null}
    </div>
  );
}
