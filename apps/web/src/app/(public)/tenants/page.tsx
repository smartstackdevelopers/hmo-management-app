import Link from "next/link";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { btnPrimary, btnSecondary } from "@/components/ui/primitives";

export default function TenantsPage() {
  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <PageHeader
        eyebrow="People / Tenants"
        title="Tenants"
        description="Organisation-scoped tenant person records. Access requires sign-in and tenants.read. Backend isolation is mandatory."
        actions={
          <>
            <Link className={btnSecondary} href="/">
              Home
            </Link>
            <Link className={btnPrimary} href="/tenants/new">
              New tenant
            </Link>
          </>
        }
      />
      <EmptyState
        title="No tenants loaded"
        description="No client-side list is loaded without a live access token."
        hint="GET /api/v1/tenants with organisation context headers after sign-in."
        action={{ label: "New tenant", href: "/tenants/new" }}
      />
    </div>
  );
}
