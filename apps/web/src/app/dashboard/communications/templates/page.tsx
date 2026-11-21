import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";

export default function TemplatesPlaceholderPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Communications"
        title="Templates"
        description="Reusable message wording for this organisation."
      />
      <EmptyState
        title="No templates to show"
        description="Message templates will appear here once they are saved for this organisation."
      />
    </div>
  );
}
