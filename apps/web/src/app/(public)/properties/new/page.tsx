import Link from "next/link";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, linkClass } from "@/components/ui/primitives";

export default function NewPropertyPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link className={`text-sm ${linkClass}`} href="/properties">
        ← Back to properties
      </Link>
      <PageHeader
        eyebrow="Portfolio / Properties"
        title="Create property"
        description="Name, address line 1, city and postcode are required."
      />
      <Card>
        <p className="text-sm leading-6 text-slate-600">
          The create form is not on this page yet. When it is submitted, the API checks those fields and records the property against your organisation.
        </p>
      </Card>
    </div>
  );
}
