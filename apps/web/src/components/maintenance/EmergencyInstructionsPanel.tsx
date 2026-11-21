import type { EmergencyContent } from "@/lib/maintenanceApi";

export function EmergencyInstructionsPanel({
  kind,
  content,
}: {
  kind: "gas" | "fire";
  content: EmergencyContent;
}) {
  const unapproved = !content.approved_for_use || content.requires_formal_approval;
  return (
    <aside className="rounded-2xl border border-red-200 bg-red-50 p-5 shadow-card">
      <p className="text-xs font-semibold uppercase tracking-wide text-red-700">
        {kind === "gas" ? "Gas" : "Fire"} safety guidance
      </p>
      {unapproved ? (
        <p className="mt-2 rounded-lg bg-amber-100 px-3 py-2 text-sm font-medium text-amber-800">
          Draft guidance — your organisation still needs to approve this wording.
        </p>
      ) : null}
      <h3 className="mt-2 text-lg font-semibold text-slate-900">{content.title || "—"}</h3>
      <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-800">{content.body || "No guidance has been added yet."}</p>
      <p className="mt-3 text-xs text-slate-600">
        This page isn&apos;t an emergency reporting channel. If anyone is in immediate danger, follow your organisation&apos;s
        procedures and call the emergency services.
      </p>
    </aside>
  );
}
