import Link from "next/link";

type UserMenuProps = {
  name?: string | null;
  email?: string | null;
  authenticated: boolean;
  authConfigured: boolean;
  roleLabel?: string;
};

function initials(value: string): string {
  const parts = value.replace(/@.*/, "").split(/[\s._-]+/).filter(Boolean);
  return (parts[0]?.[0] ?? "U").concat(parts[1]?.[0] ?? "").toUpperCase();
}

export function UserMenu({ name, email, authenticated, authConfigured, roleLabel }: UserMenuProps) {
  if (!authConfigured) {
    return <p className="text-xs text-slate-500">Sign-in is not configured in this environment.</p>;
  }

  if (!authenticated) {
    return (
      <Link
        className="inline-flex min-h-10 items-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white hover:bg-brand-800 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
        href="/auth/login?returnTo=/dashboard"
      >
        Sign in
      </Link>
    );
  }

  const display = name ?? email ?? "Signed in";

  return (
    <div className="flex items-center gap-3">
      <span
        aria-hidden="true"
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-brand-100 text-sm font-bold text-brand-700"
      >
        {initials(display)}
      </span>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-slate-900">{display}</p>
        <p className="truncate text-xs text-slate-500">{roleLabel ?? email}</p>
        <div className="mt-1 flex gap-3 text-xs font-medium">
          <Link
            className="text-brand-700 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
            href="/account"
          >
            Account
          </Link>
          <Link
            className="text-slate-500 hover:text-slate-900 hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
            href="/auth/logout"
          >
            Log out
          </Link>
        </div>
      </div>
    </div>
  );
}
