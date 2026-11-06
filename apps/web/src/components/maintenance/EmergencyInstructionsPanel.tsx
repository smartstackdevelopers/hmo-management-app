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
    <aside
      className={`rounded-lg border p-4 ${
        kind === "gas"
          ? "border-amber-400 bg-amber-50"
          : "border-orange-400 bg-orange-50"
      }`}
    >
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-700">
        Emergency {kind === "gas" ? "gas" : "fire"} guidance
      </p>
      {unapproved ? (
        <p className="mt-2 text-sm font-medium text-amber-950">
          Placeholder / draft — formal organisational approval is required before production use.
        </p>
      ) : null}
      <h3 className="mt-2 text-lg font-semibold text-slate-900">{content.title || "—"}</h3>
      <p className="mt-2 whitespace-pre-wrap text-sm text-slate-800">{content.body || "No content configured."}</p>
      <p className="mt-3 text-xs text-slate-600">
        This screen is not an emergency reporting channel. In immediate danger to life, follow your organisation&apos;s
        procedures and contact the emergency services when appropriate.
      </p>
    </aside>
  );
}
