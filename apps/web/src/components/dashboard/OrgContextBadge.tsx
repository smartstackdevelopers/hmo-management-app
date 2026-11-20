type OrgContextBadgeProps = {
  organisationId: string | null | undefined;
  roleLabel: string;
};

export function OrgContextBadge({ organisationId, roleLabel }: OrgContextBadgeProps) {
  return (
    <div
      className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2.5 text-xs text-slate-600"
      aria-label="Organisation context"
    >
      <p className="truncate text-sm font-semibold text-slate-900">
        {organisationId ? "Your organisation" : "Platform"}
      </p>
      <p className="mt-0.5 truncate">
        {roleLabel}
        {organisationId ? (
          <span className="font-mono text-slate-400" title={organisationId}>
            {" "}
            · {organisationId.slice(0, 8)}
          </span>
        ) : null}
      </p>
    </div>
  );
}
