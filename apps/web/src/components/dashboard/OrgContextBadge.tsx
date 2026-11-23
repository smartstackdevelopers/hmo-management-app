type OrgContextBadgeProps = {
  organisationId: string | null | undefined;
  roleLabel: string;
};

export function OrgContextBadge({ organisationId, roleLabel }: OrgContextBadgeProps) {
  const orgName = organisationId ? "Demo Housing" : "Demo Housing";
  return (
    <div
      className="flex items-center justify-between rounded-xl border border-slate-200/90 bg-white px-3 py-2 text-xs font-semibold text-slate-800 shadow-xs cursor-pointer hover:border-slate-300"
      aria-label="Organisation context"
    >
      <span className="truncate">{orgName}</span>
      <svg className="h-3.5 w-3.5 text-slate-400 shrink-0 ml-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
      </svg>
    </div>
  );
}
