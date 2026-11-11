"use client";

import { useState } from "react";
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
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Save failed");
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
    } catch (error) {
      setStatus(error instanceof Error ? error.message : "Save failed");
    }
  }

  return (
    <div className="space-y-8">
      <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold">Add exercise or mindfulness resource</h2>
        <select className="w-full rounded border p-2 text-sm" value={kind} onChange={(e) => setKind(e.target.value)}>
          <option value="exercise">Exercise</option>
          <option value="mindfulness">Mindfulness</option>
        </select>
        <input
          className="w-full rounded border p-2 text-sm"
          placeholder="Category (e.g. walking, breathing)"
          value={category}
          onChange={(e) => setCategory(e.target.value)}
        />
        <input
          className="w-full rounded border p-2 text-sm"
          placeholder="Title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
        />
        <textarea
          className="min-h-20 w-full rounded border p-2 text-sm"
          placeholder="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />
        <textarea
          className="min-h-20 w-full rounded border p-2 text-sm"
          placeholder="Instructions"
          value={instructions}
          onChange={(e) => setInstructions(e.target.value)}
        />
        <button
          type="button"
          className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
          disabled={!title.trim()}
          onClick={() => void saveResource()}
        >
          Save resource
        </button>
      </section>
      <section className="space-y-3 rounded-lg border border-slate-200 bg-white p-5">
        <h2 className="text-sm font-semibold">Add local wellbeing directory entry</h2>
        <input
          className="w-full rounded border p-2 text-sm"
          placeholder="Service name"
          value={dirName}
          onChange={(e) => setDirName(e.target.value)}
        />
        <select
          className="w-full rounded border p-2 text-sm"
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
        <button
          type="button"
          className="rounded bg-slate-900 px-4 py-2 text-sm text-white disabled:opacity-50"
          disabled={!dirName.trim()}
          onClick={() => void saveDirectory()}
        >
          Save directory entry
        </button>
      </section>
      {status ? <p className="text-sm text-slate-600">{status}</p> : null}
    </div>
  );
}
