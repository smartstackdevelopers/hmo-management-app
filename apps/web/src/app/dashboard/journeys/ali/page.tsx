import Link from "next/link";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { requireAuthenticatedSession } from "@/lib/session";

const STEPS = [
  { n: 1, who: "Organisation Admin", what: "Assign Support Worker to tenant caseload", href: "/dashboard/case-assignments" },
  { n: 2, who: "Support Worker", what: "Daily log — water leak under sink (human-written)", href: "/dashboard/support-worker" },
  { n: 3, who: "Support Worker", what: "Maintenance request with approval required", href: "/dashboard/maintenance" },
  { n: 4, who: "Organisation Admin", what: "Approve maintenance request", href: "/dashboard/org-workflows/approvals" },
  { n: 5, who: "Organisation Admin", what: "Verify reporting dashboard", href: "/dashboard/reports" },
];

export default async function AliJourneyGuidePage() {
  await requireAuthenticatedSession("/dashboard/journeys/ali");

  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <PageHeader
        eyebrow="F2.15"
        title="Ali journey (manual workflow)"
        description="Proposal-aligned path: manual note → repair → admin approval. No AI automation required."
      />
      <ol className="list-decimal space-y-4 pl-5 text-sm text-slate-800">
        {STEPS.map((s) => (
          <li key={s.n}>
            <span className="font-medium">{s.who}:</span> {s.what}{" "}
            <Link className="text-blue-700 underline" href={s.href}>
              Open
            </Link>
          </li>
        ))}
      </ol>
      <p className="text-xs text-slate-600">
        Automated verifier: <code>pytest tests/test_f215_ali_end_to_end.py -m postgres</code>. Use synthetic tenants only.
      </p>
    </div>
  );
}
