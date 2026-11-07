import { PageHeader } from "@/components/dashboard/PageHeader";

export default function TranslationsPlaceholderPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="F2.12"
        title="Translation review"
        description="Translations store originals separately. Default provider is a test echo — see docs/architecture/COMMUNICATION_PLATFORM_ARCHITECTURE.md"
      />
    </div>
  );
}
