"use client";

import { useCallback, useEffect, useState } from "react";
import {
  createChecklistItem,
  evidencePackDownloadUrl,
  evidenceStatusLabel,
  fetchChecklist,
  fetchItemHistory,
  fetchReadiness,
  generateEvidencePack,
  isBlockingEvidenceStatus,
  listEvidencePacks,
  packReadinessWarning,
  seedChecklist,
  updateChecklistItem,
  uploadEvidenceFile,
  type ChecklistItem,
  type EvidencePack,
  type Readiness,
  type ReviewHistory,
} from "@/lib/evidenceApi";
import { organisationRequestHeaders } from "@/lib/organisation";

const REVIEW_STATUSES = [
  "pending",
  "received",
  "under_review",
  "accepted",
  "rejected",
  "missing",
  "not_applicable",
] as const;

export function EvidencePanel({
  applicationId,
  accessToken,
  organisationId,
  role,
  canManage,
  canReview,
  canGeneratePack,
}: {
  applicationId: string;
  accessToken: string;
  organisationId: string;
  role?: string | null;
  canManage: boolean;
  canReview: boolean;
  canGeneratePack: boolean;
}) {
  const [items, setItems] = useState<ChecklistItem[] | null>(null);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [packs, setPacks] = useState<EvidencePack[]>([]);
  const [historyByItem, setHistoryByItem] = useState<Record<string, ReviewHistory[]>>({});
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [allowIncomplete, setAllowIncomplete] = useState(false);
  const [confirmGenerate, setConfirmGenerate] = useState(false);

  const auth = { accessToken, organisationId, role, applicationId };

  const reload = useCallback(async () => {
    setError(null);
    try {
      const [list, ready, packList] = await Promise.all([
        fetchChecklist(auth),
        fetchReadiness(auth),
        listEvidencePacks(auth),
      ]);
      setItems(list);
      setReadiness(ready);
      setPacks(packList);
    } catch (err) {
      setItems([]);
      setError(err instanceof Error ? err.message : "Failed to load evidence");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- auth fields are primitives
  }, [accessToken, organisationId, role, applicationId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  async function run(action: () => Promise<unknown>) {
    setPending(true);
    setError(null);
    try {
      await action();
      await reload();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setPending(false);
    }
  }

  const warning = packReadinessWarning(readiness);

  return (
    <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Evidence checklist</h2>
          <p className="text-sm text-slate-600">
            Organisation-configurable requirements — not a statutory evidence list.
          </p>
        </div>
        {canManage ? (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={pending}
              className="rounded border border-slate-300 px-3 py-1.5 text-sm"
              onClick={() => void run(() => seedChecklist(auth))}
            >
              Seed from templates
            </button>
            <button
              type="button"
              disabled={pending}
              className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white"
              onClick={() =>
                void run(() =>
                  createChecklistItem({
                    ...auth,
                    body: { title: "Additional evidence", category: "general", is_required: false },
                  }),
                )
              }
            >
              Add item
            </button>
          </div>
        ) : null}
      </div>

      {error ? <p className="text-sm text-red-700">{error}</p> : null}
      {items === null ? <p className="text-sm text-slate-500">Loading evidence…</p> : null}
      {items && items.length === 0 ? (
        <p className="text-sm text-slate-500">No checklist items yet.</p>
      ) : null}

      {readiness ? (
        <div
          className={`rounded border p-3 text-sm ${
            readiness.is_complete
              ? "border-emerald-200 bg-emerald-50 text-emerald-900"
              : "border-amber-200 bg-amber-50 text-amber-950"
          }`}
        >
          <p>
            Completeness: {readiness.required_accepted}/{readiness.required_total} required accepted
            {readiness.is_complete ? " — pack ready" : " — incomplete"}
          </p>
          {warning ? <p className="mt-1 font-medium">{warning}</p> : null}
        </div>
      ) : null}

      <ul className="space-y-3">
        {(items ?? []).map((item) => {
          const blocking = isBlockingEvidenceStatus(item.status, item.is_required);
          return (
            <li
              key={item.id}
              className={`rounded border p-3 ${
                item.status === "rejected" || item.status === "missing" || blocking
                  ? "border-amber-300 bg-amber-50/40"
                  : "border-slate-200"
              }`}
            >
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-medium text-slate-900">
                    {item.title}{" "}
                    <span className="text-xs font-normal uppercase text-slate-500">
                      {item.is_required ? "required" : "optional"} · {evidenceStatusLabel(item.status)}
                    </span>
                  </p>
                  {item.description ? (
                    <p className="text-sm text-slate-600">{item.description}</p>
                  ) : null}
                  {item.rejection_reason ? (
                    <p className="text-sm text-red-700">Rejection: {item.rejection_reason}</p>
                  ) : null}
                  <p className="text-xs text-slate-500">
                    Linked files: {item.file_ids.length}
                  </p>
                </div>
                {canManage ? (
                  <label className="text-xs text-slate-700">
                    Upload
                    <input
                      type="file"
                      className="mt-1 block text-xs"
                      disabled={pending}
                      onChange={(event) => {
                        const file = event.target.files?.[0];
                        if (!file) return;
                        void run(() =>
                          uploadEvidenceFile({
                            accessToken,
                            organisationId,
                            role,
                            itemId: item.id,
                            file,
                          }),
                        );
                        event.target.value = "";
                      }}
                    />
                  </label>
                ) : null}
              </div>

              {canReview ? (
                <form
                  className="mt-3 grid gap-2 sm:grid-cols-3"
                  onSubmit={(event) => {
                    event.preventDefault();
                    const form = new FormData(event.currentTarget);
                    const status = String(form.get("status"));
                    const rejection_reason = String(form.get("rejection_reason") || "");
                    const reviewer_notes = String(form.get("reviewer_notes") || "");
                    void run(() =>
                      updateChecklistItem({
                        accessToken,
                        organisationId,
                        role,
                        itemId: item.id,
                        body: {
                          status,
                          reviewer_notes: reviewer_notes || undefined,
                          rejection_reason:
                            status === "rejected" ? rejection_reason || undefined : undefined,
                        },
                      }),
                    );
                  }}
                >
                  <select
                    name="status"
                    defaultValue={item.status}
                    className="rounded border px-2 py-1.5 text-sm"
                  >
                    {REVIEW_STATUSES.map((status) => (
                      <option key={status} value={status}>
                        {evidenceStatusLabel(status)}
                      </option>
                    ))}
                  </select>
                  <input
                    name="reviewer_notes"
                    placeholder="Reviewer notes"
                    className="rounded border px-2 py-1.5 text-sm"
                  />
                  <input
                    name="rejection_reason"
                    placeholder="Rejection reason (if rejecting)"
                    className="rounded border px-2 py-1.5 text-sm"
                  />
                  <button
                    type="submit"
                    disabled={pending}
                    className="rounded bg-slate-800 px-3 py-1.5 text-sm text-white sm:col-span-3 sm:w-fit"
                  >
                    Update status
                  </button>
                </form>
              ) : null}

              <button
                type="button"
                className="mt-2 text-xs text-teal-800 underline"
                onClick={() =>
                  void (async () => {
                    try {
                      const history = await fetchItemHistory({
                        accessToken,
                        organisationId,
                        role,
                        itemId: item.id,
                      });
                      setHistoryByItem((prev) => ({ ...prev, [item.id]: history }));
                    } catch (err) {
                      setError(err instanceof Error ? err.message : "History failed");
                    }
                  })()
                }
              >
                Show review history
              </button>
              {(() => {
                const history = historyByItem[item.id];
                if (!history?.length) return null;
                return (
                  <ul className="mt-1 space-y-1 text-xs text-slate-600">
                    {history.map((h) => (
                      <li key={h.id}>
                        {h.from_status ?? "—"} → {h.to_status}
                        {h.note ? ` · ${h.note}` : ""} · {new Date(h.created_at).toLocaleString()}
                      </li>
                    ))}
                  </ul>
                );
              })()}
            </li>
          );
        })}
      </ul>

      {canGeneratePack ? (
        <div className="space-y-3 border-t border-slate-100 pt-4">
          <h3 className="font-medium text-slate-900">Evidence pack</h3>
          {warning ? (
            <p className="text-sm text-amber-900" role="status">
              {warning}. Generating without confirmation would misrepresent completeness.
            </p>
          ) : (
            <p className="text-sm text-emerald-800">Required evidence is complete.</p>
          )}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={allowIncomplete}
              onChange={(event) => setAllowIncomplete(event.target.checked)}
            />
            Allow incomplete draft pack (outstanding items marked)
          </label>
          {!confirmGenerate ? (
            <button
              type="button"
              disabled={pending || (!!warning && !allowIncomplete)}
              className="rounded bg-teal-700 px-3 py-1.5 text-sm text-white disabled:opacity-50"
              onClick={() => setConfirmGenerate(true)}
            >
              Prepare pack generation
            </button>
          ) : (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                disabled={pending}
                className="rounded bg-teal-800 px-3 py-1.5 text-sm text-white"
                onClick={() =>
                  void run(async () => {
                    await generateEvidencePack({ ...auth, allowIncomplete });
                    setConfirmGenerate(false);
                  })
                }
              >
                Confirm generate {allowIncomplete && warning ? "draft" : "pack"}
              </button>
              <button
                type="button"
                className="rounded border px-3 py-1.5 text-sm"
                onClick={() => setConfirmGenerate(false)}
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      ) : null}

      <div className="space-y-2 border-t border-slate-100 pt-4">
        <h3 className="font-medium text-slate-900">Generated packs</h3>
        {packs.length === 0 ? (
          <p className="text-sm text-slate-500">No packs generated yet.</p>
        ) : (
          <ul className="space-y-2 text-sm">
            {packs.map((pack) => (
              <li key={pack.id} className="flex flex-wrap items-center justify-between gap-2">
                <span>
                  {new Date(pack.generated_at).toLocaleString()} ·{" "}
                  {pack.is_complete ? "complete" : "incomplete draft"} · {pack.status}
                  {pack.outstanding_summary ? ` · outstanding: ${pack.outstanding_summary}` : ""}
                </span>
                <a
                  className="text-teal-800 underline"
                  href={evidencePackDownloadUrl(pack.id)}
                  onClick={async (event) => {
                    event.preventDefault();
                    const response = await fetch(evidencePackDownloadUrl(pack.id), {
                      headers: {
                        Authorization: `Bearer ${accessToken}`,
                        ...organisationRequestHeaders({ organisationId, role }),
                      },
                    });
                    if (!response.ok) {
                      setError(await response.text());
                      return;
                    }
                    const blob = await response.blob();
                    const url = URL.createObjectURL(blob);
                    const anchor = document.createElement("a");
                    anchor.href = url;
                    anchor.download = `evidence-pack-${pack.id}.pdf`;
                    anchor.click();
                    URL.revokeObjectURL(url);
                  }}
                >
                  Download PDF
                </a>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
