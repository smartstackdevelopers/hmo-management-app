import { redirect } from "next/navigation";
import { auth0, isAuth0Configured } from "@/lib/auth0";
import { canAny } from "@/lib/rbac";
import { requireAuthenticatedSession } from "@/lib/session";
import { approveRegistrationAction, rejectRegistrationAction } from "./actions";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

export default async function RegistrationApprovalsPage() {
  const session = await requireAuthenticatedSession("/dashboard/approvals/registrations");
  const role = session.authorization?.active_role;
  if (role !== "super_admin" && role !== "organisation_admin") {
    redirect("/unauthorized");
  }
  if (!isAuth0Configured() || !auth0) {
    return <p className="p-6">Authentication is not configured.</p>;
  }
  const token = (await auth0.getAccessToken())?.token;
  if (!token) {
    return <p className="p-6">Missing access token.</p>;
  }
  const response = await fetch(`${API_BASE}/api/v1/auth/registration-requests`, {
    headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
    cache: "no-store",
  });
  if (!response.ok) {
    return <p className="p-6">Could not load registration requests ({response.status}).</p>;
  }
  const payload = (await response.json()) as {
    items: Array<{
      id: string;
      display_name: string | null;
      email: string | null;
      requested_role: string;
      organisation_id: string | null;
      status: string;
      created_at: string | null;
    }>;
  };
  const pending = payload.items.filter((item) => item.status === "pending");
  const notifications = await fetch(`${API_BASE}/api/v1/auth/notifications`, {
    headers: { Authorization: `Bearer ${token}`, Accept: "application/json" },
    cache: "no-store",
  })
    .then((r) => (r.ok ? r.json() : { pending_count: 0, items: [] }))
    .catch(() => ({ pending_count: 0, items: [] }));

  return (
    <main className="mx-auto max-w-4xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold">Registration approvals</h1>
        <p className="text-slate-600">
          Pending notifications: <strong>{notifications.pending_count ?? 0}</strong>
        </p>
      </header>
      <div className="space-y-3">
        {pending.length === 0 ? (
          <p className="text-slate-600">No pending registration requests.</p>
        ) : (
          pending.map((item) => (
            <article key={item.id} className="rounded border border-slate-200 bg-white p-4 shadow-sm">
              <h2 className="text-lg font-semibold">{item.display_name || "Applicant"}</h2>
              <p className="text-sm text-slate-600">{item.email}</p>
              <p className="mt-1 text-sm">
                Requested role: <strong>{item.requested_role}</strong>
              </p>
              <p className="text-xs text-slate-500">Org: {item.organisation_id || "—"}</p>
              <div className="mt-3 flex gap-2">
                <form action={approveRegistrationAction}>
                  <input type="hidden" name="request_id" value={item.id} />
                  <button type="submit" className="rounded bg-teal-700 px-3 py-2 text-sm font-semibold text-white">
                    Approve
                  </button>
                </form>
                <form action={rejectRegistrationAction} className="flex gap-2">
                  <input type="hidden" name="request_id" value={item.id} />
                  <input
                    name="rejection_reason"
                    placeholder="Rejection reason"
                    className="rounded border px-2 py-1 text-sm"
                    required
                  />
                  <button type="submit" className="rounded border border-red-300 px-3 py-2 text-sm text-red-700">
                    Reject
                  </button>
                </form>
              </div>
            </article>
          ))
        )}
      </div>
      {!canAny(session.authorization?.permissions, ["role_assignments.manage"]) ? null : null}
    </main>
  );
}
