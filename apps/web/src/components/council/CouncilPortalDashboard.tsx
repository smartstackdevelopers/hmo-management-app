"use client";

import { useEffect, useMemo, useState, useTransition } from "react";
import {
  createCouncilShare,
  fetchCouncilAdminDashboard,
  fetchCouncilOfficerInbox,
  inviteCouncilOfficer,
  revokeCouncilShare,
} from "@/lib/councilPortalApi";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  canManage: boolean;
};

export function CouncilPortalDashboard({ accessToken, organisationId, role, canManage }: Props) {
  const auth = useMemo(() => ({ accessToken, organisationId, role }), [accessToken, organisationId, role]);
  const [dash, setDash] = useState<Record<string, unknown> | null>(null);
  const [inbox, setInbox] = useState<Record<string, unknown>[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [pending, startTransition] = useTransition();
  const [officerUserId, setOfficerUserId] = useState("");
  const [applicationId, setApplicationId] = useState("");
  const [purpose, setPurpose] = useState("Statutory housing review");

  const refresh = () => {
    startTransition(async () => {
      setError(null);
      try {
        if (canManage) {
          const d = await fetchCouncilAdminDashboard(auth);
          setDash(d);
        } else {
          const i = await fetchCouncilOfficerInbox(auth);
          setInbox(i.items);
          setDash({ disclaimer: i.disclaimer });
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : "Failed to load Council Portal");
      }
    });
  };

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const officers = (dash?.officers as Record<string, unknown>[] | undefined) ?? [];
  const shares = (dash?.shares as Record<string, unknown>[] | undefined) ?? [];

  return (
    <div className="space-y-8">
      <div>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-brand-700">Operations</p>
        <h1 className="mt-1.5 text-2xl font-bold tracking-tight text-slate-900">Council portal</h1>
        <p className="mt-1 text-sm text-slate-600">
          {String(
            dash?.disclaimer ??
              "Optional add-on. Council officers are not a core HMore role. Only explicitly shared applications are visible.",
          )}
        </p>
      </div>

      {error ? <p className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800">{error}</p> : null}
      {pending && !dash ? <p className="text-sm text-slate-500">Loading…</p> : null}

      {canManage ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
              <div className="text-xs uppercase text-slate-500">Active officers</div>
              <div className="mt-1 text-2xl font-semibold">{String(dash?.active_officers ?? "—")}</div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
              <div className="text-xs uppercase text-slate-500">Active shares</div>
              <div className="mt-1 text-2xl font-semibold">{String(dash?.active_shares ?? "—")}</div>
            </div>
          </div>

          <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
            <h2 className="text-sm font-medium">Invite council officer (add-on identity)</h2>
            <input
              className="block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
              placeholder="Existing user UUID"
              value={officerUserId}
              onChange={(e) => setOfficerUserId(e.target.value)}
            />
            <button
              type="button"
              className="inline-flex h-10 items-center justify-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
              onClick={() =>
                startTransition(async () => {
                  try {
                    await inviteCouncilOfficer(auth, { user_id: officerUserId });
                    setOfficerUserId("");
                    refresh();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Invite failed");
                  }
                })
              }
            >
              Invite officer
            </button>
          </section>

          <section className="space-y-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
            <h2 className="text-sm font-medium">Share housing application</h2>
            <input
              className="block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
              placeholder="Application UUID"
              value={applicationId}
              onChange={(e) => setApplicationId(e.target.value)}
            />
            <input
              className="block h-10 w-full rounded-lg border border-slate-300 bg-white px-3 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
              value={purpose}
              onChange={(e) => setPurpose(e.target.value)}
            />
            <button
              type="button"
              className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
              onClick={() =>
                startTransition(async () => {
                  try {
                    await createCouncilShare(auth, {
                      application_id: applicationId,
                      purpose,
                      include_approval_history: true,
                      include_evidence: false,
                      scopes: ["application_status", "approval_history"],
                    });
                    setApplicationId("");
                    refresh();
                  } catch (e) {
                    setError(e instanceof Error ? e.message : "Share failed");
                  }
                })
              }
            >
              Create share
            </button>
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-medium">Officers</h2>
            {!officers.length ? (
              <p className="text-sm text-slate-500">No officers yet.</p>
            ) : (
              <ul className="space-y-2">
                {officers.map((o) => (
                  <li key={String(o.id)} className="rounded-2xl border border-slate-200 bg-white p-4 text-sm shadow-card">
                    {String(o.display_name ?? o.user_id)} · {String(o.status)} · add-on role{" "}
                    {String(o.addon_role_label)}
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className="space-y-2">
            <h2 className="text-sm font-medium">Shares</h2>
            {!shares.length ? (
              <p className="text-sm text-slate-500">No shares yet.</p>
            ) : (
              <ul className="space-y-2">
                {shares.map((s) => (
                  <li key={String(s.id)} className="flex flex-wrap items-center justify-between gap-2 rounded-2xl border border-slate-200 bg-white p-4 text-sm shadow-card">
                    <span>
                      App {String(s.application_id)} · {String(s.status)} · {String(s.purpose)}
                    </span>
                    {s.status === "active" ? (
                      <button
                        type="button"
                        className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
                        onClick={() =>
                          startTransition(async () => {
                            await revokeCouncilShare(auth, String(s.id));
                            refresh();
                          })
                        }
                      >
                        Revoke
                      </button>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </section>
        </>
      ) : (
        <section className="space-y-2">
          <h2 className="text-sm font-medium">Shared applications inbox</h2>
          {!inbox.length ? (
            <p className="rounded-lg border border-dashed p-6 text-sm text-slate-500">
              No applications have been shared with you for this organisation.
            </p>
          ) : (
            <ul className="space-y-2">
              {inbox.map((item) => (
                <li key={String(item.share_id)} className="rounded-2xl border border-slate-200 bg-white p-4 text-sm shadow-card">
                  {String(item.reference_number)} · {String(item.status)} · tenant records exposed:{" "}
                  {String(item.tenant_records_exposed)}
                </li>
              ))}
            </ul>
          )}
        </section>
      )}

      <button type="button" className="inline-flex h-10 items-center justify-center rounded-lg border border-slate-200 bg-white px-4 text-sm font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600" onClick={refresh}>
        Refresh
      </button>
    </div>
  );
}
