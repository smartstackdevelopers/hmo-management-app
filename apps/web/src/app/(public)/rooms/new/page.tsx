import Link from "next/link";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Card, linkClass } from "@/components/ui/primitives";

export default function NewRoomPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link className={`text-sm ${linkClass}`} href="/rooms">
        ← Back to rooms
      </Link>
      <PageHeader
        eyebrow="Portfolio / Rooms"
        title="Create room"
        description="A room needs a property and a label. Maximum occupancy must be at least 1 when you set it. Archived properties cannot take new rooms."
      />
      <Card>
        <p className="text-sm leading-6 text-slate-600">
          The create form is not on this page yet. Two rooms in the same property cannot share a label.
        </p>
      </Card>
    </div>
  );
}
