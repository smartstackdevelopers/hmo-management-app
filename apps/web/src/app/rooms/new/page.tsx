import Link from "next/link";

export default function NewRoomPage() {
  return (
    <div className="mx-auto max-w-xl space-y-6">
      <h1 className="text-3xl font-semibold text-forest-900">Create room</h1>
      <p className="text-slate-700">
        API: <code className="rounded bg-slate-100 px-1">POST /api/v1/rooms</code>. Required:
        property_id, label. max_occupancy must be positive when set. Archived properties reject new
        rooms.
      </p>
      <div className="rounded-lg border border-slate-200 bg-white p-5 text-sm text-slate-600">
        Duplicate labels on the same property return HTTP 409 from the API.
      </div>
      <Link className="text-sm text-teal-800 hover:underline" href="/rooms">
        Back to rooms
      </Link>
    </div>
  );
}
