import Link from "next/link";

type UserMenuProps = {
  name?: string | null;
  email?: string | null;
  authenticated: boolean;
  authConfigured: boolean;
};

export function UserMenu({ name, email, authenticated, authConfigured }: UserMenuProps) {
  if (!authConfigured) {
    return (
      <p className="text-xs text-emerald-100/80">Auth0 not configured in this environment.</p>
    );
  }

  if (!authenticated) {
    return (
      <Link
        className="inline-flex rounded-md bg-white/15 px-3 py-2 text-sm font-medium text-white hover:bg-white/25 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200"
        href="/auth/login?returnTo=/dashboard"
      >
        Sign in
      </Link>
    );
  }

  return (
    <div className="space-y-2 text-sm text-emerald-50">
      <p className="font-medium text-white">{name ?? "Signed in"}</p>
      {email ? <p className="break-all text-xs text-emerald-100/80">{email}</p> : null}
      <div className="flex flex-wrap gap-2 pt-1">
        <Link
          className="rounded-md px-2 py-1 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200"
          href="/account"
        >
          Account
        </Link>
        <Link
          className="rounded-md px-2 py-1 hover:bg-white/10 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-200"
          href="/auth/logout"
        >
          Log out
        </Link>
      </div>
    </div>
  );
}
