import Link from "next/link";
import { redirect } from "next/navigation";
import { auth0, isAuth0Configured } from "@/lib/auth0";

export default async function AccountPage() {
  if (!isAuth0Configured() || !auth0) {
    return (
      <div className="mx-auto max-w-xl space-y-4">
        <h1 className="text-3xl font-semibold text-forest-900">Sign-in not configured</h1>
        <p className="text-slate-700">
          Auth0 environment variables are missing. Create a UK or EU Auth0 tenant and copy the
          values from <code className="rounded bg-slate-100 px-1">apps/web/.env.example</code>.
        </p>
        <p className="text-sm text-slate-600">
          Live login and MFA remain unverified until a real tenant is connected.
        </p>
      </div>
    );
  }

  const session = await auth0.getSession();
  if (!session) {
    redirect("/auth/login?returnTo=/account");
  }

  const user = session.user;

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h1 className="text-3xl font-semibold text-forest-900">Account</h1>
        <p className="mt-2 text-slate-700">
          Authenticated through Auth0. Permissions are enforced by the API (F1.4). Role
          dashboards ship in F1.9.
        </p>
      </div>
      <dl className="space-y-3 rounded-lg border border-slate-200 bg-white p-5 text-sm">
        <div>
          <dt className="font-medium text-slate-500">Subject</dt>
          <dd className="mt-1 break-all text-slate-900">{user.sub}</dd>
        </div>
        <div>
          <dt className="font-medium text-slate-500">Email</dt>
          <dd className="mt-1 text-slate-900">{user.email ?? "not provided"}</dd>
        </div>
        <div>
          <dt className="font-medium text-slate-500">Name</dt>
          <dd className="mt-1 text-slate-900">{user.name ?? user.nickname ?? "not provided"}</dd>
        </div>
      </dl>
      <div className="flex gap-3">
        <Link
          className="rounded-md bg-teal-700 px-4 py-2 text-sm font-medium text-white hover:bg-teal-800"
          href="/auth/logout"
        >
          Log out
        </Link>
        <Link className="rounded-md px-4 py-2 text-sm text-forest-900 hover:bg-slate-100" href="/">
          Home
        </Link>
      </div>
    </div>
  );
}
