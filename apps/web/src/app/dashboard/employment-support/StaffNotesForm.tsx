"use client";

import { useState } from "react";
import { btnPrimary, inputClass } from "@/components/ui/primitives";
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
    } catch {
      setStatus("Save failed.");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <h2 className="text-base font-semibold text-slate-900">Support notes</h2>
      <p className="text-sm text-slate-600">
        Permitted employment support notes only. Do not paste private CV content or contact details
        unless policy allows.
      </p>
      <textarea
        className={`${inputClass} h-auto min-h-28 py-2`}
        value={notes}
        onChange={(event) => setNotes(event.target.value)}
      />
      <button
        type="button"
        disabled={saving || !notes.trim()}
        onClick={() => void onSave()}
        className={btnPrimary}
      >
        {saving ? "Saving…" : "Save notes"}
      </button>
      {status ? <p className="text-sm text-slate-600">{status}</p> : null}
    </div>
  );
}
