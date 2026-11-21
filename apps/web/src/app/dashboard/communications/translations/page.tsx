import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";

export default function TranslationsPlaceholderPage() {
  return (
    <div className="space-y-6">
      <PageHeader
        eyebrow="Communications"
        title="Translation review"
        description="Review a translation before it is sent. The original wording is kept."
      />
      <EmptyState
        title="No translations to review"
        description="Translations waiting for a person to check them will appear here."
      />
    </div>
  );
}
