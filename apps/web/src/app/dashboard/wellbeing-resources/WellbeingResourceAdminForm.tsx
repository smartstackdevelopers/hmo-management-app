"use client";

import { useState } from "react";
import { btnPrimary, inputClass, labelClass } from "@/components/ui/primitives";
import { createWellbeingDirectoryEntry, createWellbeingResource } from "@/lib/wellbeingApi";

export function WellbeingResourceAdminForm(props: {
  accessToken: string;
  organisationId: string;
  role?: string | null;
}) {
  const [kind, setKind] = useState("exercise");
  const [category, setCategory] = useState("walking");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [dirName, setDirName] = useState("");
  const [dirCategory, setDirCategory] = useState("community_wellbeing");
  const [status, setStatus] = useState<string | null>(null);

  async function saveResource() {
    setStatus(null);
    try {
      await createWellbeingResource({
        accessToken: props.accessToken,
        organisationId: props.organisationId,
        role: props.role,
        body: {
          kind,
          category,
          title,
          description: description || null,
          instructions: instructions || null,
          verification_status: "verified",
          safety_notes: "General information only. Seek professional advice if needed.",
        },
      });
      setStatus("Resource saved.");
      setTitle("");
      setDescription("");
      setInstructions("");
    } catch {
      setStatus("Save failed");
    }
  }

  async function saveDirectory() {
    setStatus(null);
    try {
      await createWellbeingDirectoryEntry({
        accessToken: props.accessToken,
        organisationId: props.organisationId,
        role: props.role,
        body: {
          name: dirName,
          category: dirCategory,
          description: description || null,
          verification_status: "verified",
          is_clinical: false,
        },
      });
      setStatus("Directory entry saved.");
      setDirName("");
    } catch {
      setStatus("Save failed");
    }
  }

  return (
    <div className="space-y-8">
      <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        <h2 className="text-base font-semibold text-slate-900">Add exercise or mindfulness resource</h2>
        <div className="space-y-1.5">
          <label htmlFor="wellbeing-kind" className={labelClass}>Kind</label>
          <select id="wellbeing-kind" className={inputClass} value={kind} onChange={(e) => setKind(e.target.value)}>
            <option value="exercise">Exercise</option>
            <option value="mindfulness">Mindfulness</option>
          </select>
        </div>
        <div className="space-y-1.5">
          <label htmlFor="wellbeing-category" className={labelClass}>Category</label>
          <input id="wellbeing-category" className={inputClass} placeholder="walking, breathing" value={category} onChange={(e) => setCategory(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="wellbeing-title" className={labelClass}>Title</label>
          <input id="wellbeing-title" className={inputClass} value={title} onChange={(e) => setTitle(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="wellbeing-description" className={labelClass}>Description</label>
          <textarea id="wellbeing-description" className={`${inputClass} h-auto min-h-20 py-2`} value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="wellbeing-instructions" className={labelClass}>Instructions</label>
          <textarea id="wellbeing-instructions" className={`${inputClass} h-auto min-h-20 py-2`} value={instructions} onChange={(e) => setInstructions(e.target.value)} />
        </div>
        <div className="flex justify-end">
          <button type="button" className={btnPrimary} disabled={!title.trim()} onClick={() => void saveResource()}>
            Save resource
          </button>
        </div>
      </section>
      <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
        <h2 className="text-base font-semibold text-slate-900">Add local wellbeing directory entry</h2>
        <div className="space-y-1.5">
          <label htmlFor="wellbeing-dir-name" className={labelClass}>Service name</label>
          <input id="wellbeing-dir-name" className={inputClass} value={dirName} onChange={(e) => setDirName(e.target.value)} />
        </div>
        <div className="space-y-1.5">
          <label htmlFor="wellbeing-dir-category" className={labelClass}>Category</label>
          <select
            id="wellbeing-dir-category"
            className={inputClass}
            value={dirCategory}
            onChange={(e) => setDirCategory(e.target.value)}
          >
          <option value="community_wellbeing">Community wellbeing</option>
          <option value="mental_wellbeing_support">Mental wellbeing support</option>
          <option value="social_support">Social support</option>
          <option value="community_activities">Community activities</option>
          <option value="local_advice">Local advice</option>
          <option value="general_support">General support</option>
        </select>
        </div>
        <div className="flex justify-end">
          <button type="button" className={btnPrimary} disabled={!dirName.trim()} onClick={() => void saveDirectory()}>
            Save directory entry
          </button>
        </div>
      </section>
      {status ? <p className="text-sm text-slate-600">{status}</p> : null}
    </div>
  );
}
