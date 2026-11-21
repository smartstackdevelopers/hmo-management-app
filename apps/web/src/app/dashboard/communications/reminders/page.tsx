import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";

export default function RemindersPlaceholderPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Communications"
        title="Reminder management"
        description="Reminders that are due are sent on the organisation schedule."
      />
      <EmptyState
        title="No reminders to show"
        description="Scheduled reminders will appear here once they are recorded for this organisation."
      />
    </div>
  );
}
