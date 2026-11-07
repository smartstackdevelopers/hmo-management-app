import { PageHeader } from "@/components/dashboard/PageHeader";

export default function RemindersPlaceholderPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="F2.12"
        title="Reminder management"
        description="Create and list reminders via POST/GET /api/v1/communications/reminders. Compose UI can be added when product flows are finalised."
      />
      <p className="text-sm text-slate-600">Celery task hmore.communication.dispatch_scheduled_reminders processes due rows.</p>
    </div>
  );
}
