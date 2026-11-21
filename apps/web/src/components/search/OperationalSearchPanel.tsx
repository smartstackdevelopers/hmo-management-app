"use client";

import { useState } from "react";
import { OPERATIONAL_SEARCH_NOTICE, outcomeLabel } from "@/lib/operationalSearchView";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
  initialQuestion?: string;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const EXAMPLES = [
  "Show overdue maintenance requests",
  "Show complaints that are still open",
  "Which applications are waiting for approval?",
  "Show incidents that still require follow-up",
];

export function OperationalSearchPanel(props: Props) {
  const [question, setQuestion] = useState(props.initialQuestion ?? "");
  const [state, setState] = useState<"idle" | "loading" | "error" | "ready">("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);

  async function submit(text: string) {
    setError(null);
    setState("loading");
    try {
      const response = await fetch(`${API_BASE}/api/v1/operational-search`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${props.accessToken}`,
          "Content-Type": "application/json",
          "X-Organisation-Id": props.organisationId,
          ...(props.role ? { "X-HMore-Role": props.role } : {}),
        },
        body: JSON.stringify({ question: text }),
      });
      if (!response.ok) {
        setError(await response.text());
        setState("error");
        return;
      }
      setResult((await response.json()) as Record<string, unknown>);
      setState("ready");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
      setState("error");
    }
  }

  const items = (result?.items as Array<Record<string, unknown>> | undefined) ?? [];
  const outcome = String(result?.outcome ?? "");

  return (
    <section className="space-y-4 rounded-2xl border border-slate-200 bg-white p-5 shadow-card">
      <h2 className="text-lg font-semibold text-slate-900">Operational search</h2>
      <p className="text-sm font-medium text-amber-950">{OPERATIONAL_SEARCH_NOTICE}</p>
      <label className="block text-sm text-slate-700">
        Question
        <textarea
          className="mt-1 block w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 focus:border-brand-600 focus:outline-none focus:ring-2 focus:ring-brand-100"
          rows={3}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="inline-flex h-10 items-center justify-center rounded-lg bg-brand-700 px-4 text-sm font-semibold text-white shadow-sm hover:bg-brand-800 disabled:cursor-not-allowed disabled:opacity-60 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600 focus-visible:ring-offset-2"
          disabled={state === "loading" || question.trim().length === 0}
          onClick={() => void submit(question)}
        >
          {state === "loading" ? "Searching…" : "Search"}
        </button>
      </div>
      <div className="flex flex-wrap gap-2">
        {EXAMPLES.map((example) => (
          <button
            key={example}
            type="button"
            className="inline-flex h-8 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 hover:bg-slate-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-600"
            onClick={() => {
              setQuestion(example);
              void submit(example);
            }}
          >
            {example}
          </button>
        ))}
      </div>
      {state === "error" && error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      {state === "ready" && result ? (
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-900">{outcomeLabel(outcome)}</p>
          <p className="text-sm text-slate-700">{String(result.message ?? "")}</p>
          {result.interpretation ? (
            <p className="text-xs text-slate-600">
              Interpreted as {JSON.stringify(result.interpretation)} (not a database command)
            </p>
          ) : null}
          {outcome === "results" && items.length === 0 ? (
            <p className="text-sm text-slate-700">No matching records in your organisation.</p>
          ) : null}
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={String(item.id)} className="border-b border-amber-100 pb-2 text-sm">
                <a className="font-medium text-brand-700 underline" href={String(item.href)}>
                  {String(item.title)}
                </a>
                <p className="text-xs text-slate-600">
                  {String(item.record_type)} · {String(item.status)}
                  {item.relevant_date ? ` · ${String(item.relevant_date)}` : ""}
                </p>
                <p className="text-xs text-slate-500">{String(item.summary ?? "")}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
