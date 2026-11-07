import { PageHeader } from "@/components/dashboard/PageHeader";

export default function TemplatesPlaceholderPage() {
  return (
    <div className="space-y-4">
      <PageHeader
        eyebrow="F2.12"
        title="Templates"
        description="GET/POST/PATCH /api/v1/communications/templates — placeholders are allow-listed server-side."
      />
    </div>
  );
}
