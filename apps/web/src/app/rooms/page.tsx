import Link from "next/link";

export default function RoomsPage() {
  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-forest-900">Rooms</h1>
        <p className="mt-2 text-slate-700">
          Rooms inherit organisation ownership from their property. Filter with{" "}
          <code className="rounded bg-slate-100 px-1">property_id</code>. Requires{" "}
          <code className="rounded bg-slate-100 px-1">rooms.read</code>.
        </p>
      </div>
      <div className="rounded-lg border border-dashed border-slate-300 bg-white p-8 text-center text-slate-600">
        Empty state — load via <code className="rounded bg-slate-100 px-1">GET /api/v1/rooms</code>.
      </div>
      <div className="flex gap-3">
        <Link className="rounded-md bg-teal-700 px-4 py-2 text-sm text-white" href="/rooms/new">
          New room
        </Link>
        <Link className="rounded-md px-4 py-2 text-sm text-forest-900 hover:bg-slate-100" href="/properties">
          Properties
        </Link>
      </div>
    </div>
  );
}
