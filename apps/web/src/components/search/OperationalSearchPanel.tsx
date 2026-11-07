"use client";

import { useState } from "react";
import { OPERATIONAL_SEARCH_NOTICE, outcomeLabel } from "@/lib/operationalSearchView";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";
const EXAMPLES = [
  "Show overdue maintenance requests",
  "Show complaints that are still open",
  "Which applications are waiting for approval?",
  "Show incidents that still require follow-up",
];

export function OperationalSearchPanel(props: Props) {
  const [question, setQuestion] = useState("");
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
    <section className="space-y-4 rounded-lg border border-amber-200 bg-amber-50/40 p-4">
      <h2 className="text-lg font-semibold text-forest-900">Operational search</h2>
      <p className="text-sm font-medium text-amber-950">{OPERATIONAL_SEARCH_NOTICE}</p>
      <label className="block text-sm text-forest-800">
        Question
        <textarea
          className="mt-1 w-full rounded-md border border-forest-200 p-2 text-sm"
          rows={3}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
        />
      </label>
      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          className="rounded-md bg-teal-700 px-3 py-2 text-sm text-white disabled:opacity-60"
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
            className="rounded-md border border-forest-300 px-2 py-1 text-xs"
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
          <p className="text-sm font-medium text-forest-900">{outcomeLabel(outcome)}</p>
          <p className="text-sm text-forest-800">{String(result.message ?? "")}</p>
          {result.interpretation ? (
            <p className="text-xs text-forest-700">
              Interpreted as {JSON.stringify(result.interpretation)} (not a database command)
            </p>
          ) : null}
          {outcome === "results" && items.length === 0 ? (
            <p className="text-sm text-forest-800">No matching records in your organisation.</p>
          ) : null}
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={String(item.id)} className="border-b border-amber-100 pb-2 text-sm">
                <a className="font-medium text-teal-800 underline" href={String(item.href)}>
                  {String(item.title)}
                </a>
                <p className="text-xs text-forest-700">
                  {String(item.record_type)} · {String(item.status)}
                  {item.relevant_date ? ` · ${String(item.relevant_date)}` : ""}
                </p>
                <p className="text-xs text-forest-600">{String(item.summary ?? "")}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
