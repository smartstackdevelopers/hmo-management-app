import Link from "next/link";
import { redirect } from "next/navigation";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";

export default async function OccupancySurveyShellPage() {
  const session = await requireAuthenticatedSession("/dashboard/occupancy-survey");
  const permissions = session.authorization?.permissions;
  if (
    session.authorization &&
    !canAny(permissions, [
      "occupancy.read",
      "occupancy.alerts.manage",
      "inspections.manage",
    ])
  ) {
    redirect("/unauthorized");
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <PageHeader
        eyebrow="Housing"
        title="Occupancy site survey"
        description="Feasibility and site-survey foundation only. Camera capture, live video, and occupancy detection are not part of this release."
      />
      <EmptyState
        title="No survey form on this page"
        description="Site surveys are recorded for feasibility only. This page does not capture video or count people."
      />
      <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
        <li>No cameras or people-counting software.</li>
        <li>Feasibility status is operational only — not a legal certification.</li>
        <li>
          Evidence attachments use private files (
          <Link className="text-brand-700 underline" href="/dashboard/files">
            files shell
          </Link>
          ).
        </li>
      </ul>
    </div>
  );
}
