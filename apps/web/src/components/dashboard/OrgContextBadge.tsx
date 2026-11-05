type OrgContextBadgeProps = {
  organisationId: string | null | undefined;
  roleLabel: string;
};

export function OrgContextBadge({ organisationId, roleLabel }: OrgContextBadgeProps) {
  return (
    <div
      className="rounded-md border border-emerald-800/30 bg-emerald-950/40 px-3 py-2 text-xs text-emerald-50"
      aria-label="Organisation context"
    >
      <p className="font-semibold uppercase tracking-wide text-emerald-200/90">Context</p>
      <p className="mt-1">Role: {roleLabel}</p>
      <p className="mt-0.5 break-all">
        Organisation:{" "}
        {organisationId ? (
          <span className="font-mono">{organisationId}</span>
        ) : (
          <span>Platform / not selected</span>
        )}
      </p>
    </div>
  );
}
