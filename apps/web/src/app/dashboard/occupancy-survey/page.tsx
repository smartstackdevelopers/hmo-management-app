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
        eyebrow="F1.10"
        title="Occupancy site survey"
        description="Feasibility and site-survey foundation only. Camera capture, live video, and occupancy detection are not part of this release."
      />
      <EmptyState
        title="Use the checklist pack and API"
        description="Create and update surveys via POST/PATCH /api/v1/occupancy-surveys. Full interactive survey forms are a later enhancement."
        hint="Client checklist: docs/operations/OCCUPANCY_SITE_SURVEY_CHECKLIST.md"
      />
      <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
        <li>No cameras, CV, or people-counting software in F1.10.</li>
        <li>Feasibility status is operational only — not a legal certification.</li>
        <li>
          Evidence attachments use private files (
          <Link className="text-teal-800 underline" href="/dashboard/files">
            files shell
          </Link>
          ).
        </li>
      </ul>
    </div>
  );
}
