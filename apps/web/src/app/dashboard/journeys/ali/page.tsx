import { ActionTile } from "@/components/ui/primitives";
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
        eyebrow="Operations"
        title="Ali journey (manual workflow)"
        description="Proposal-aligned path: manual note → repair → admin approval. No AI automation required."
      />
      <div className="grid gap-3">
        {STEPS.map((step) => (
          <ActionTile
            key={step.n}
            href={step.href}
            title={`${step.n}. ${step.who}`}
            description={step.what}
            initials={String(step.n)}
          />
        ))}
      </div>
      <p className="text-sm text-slate-500">Use a synthetic tenant for this walkthrough.</p>
    </div>
  );
}
