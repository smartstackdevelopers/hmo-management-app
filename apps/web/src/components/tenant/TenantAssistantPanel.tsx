"use client";

import { useState } from "react";
import { ASSISTANT_NOTICE, sourceLabel } from "@/lib/tenantAssistantView";

type Props = {
  accessToken: string;
  organisationId: string;
  role?: string | null;
};

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

type ChatMessage = {
  role: string;
  body: string;
  source_refs?: Array<{ title?: string; source_type?: string; content_id?: string }>;
};

export function TenantAssistantPanel(props: Props) {
  const [question, setQuestion] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [state, setState] = useState<"idle" | "loading" | "error">("idle");
  const [error, setError] = useState<string | null>(null);

  async function send() {
    const text = question.trim();
    if (text.length < 3) return;
    setError(null);
    setState("loading");
    setMessages((prev) => [...prev, { role: "user", body: text }]);
    setQuestion("");
    try {
      const response = await fetch(`${API_BASE}/api/v1/tenant-assistant/ask`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${props.accessToken}`,
          "Content-Type": "application/json",
          "X-Organisation-Id": props.organisationId,
          ...(props.role ? { "X-HMore-Role": props.role } : {}),
        },
        body: JSON.stringify({
          question: text,
          conversation_id: conversationId,
        }),
      });
      if (!response.ok) {
        setError(await response.text());
        setState("error");
        return;
      }
      const data = (await response.json()) as {
        conversation_id: string;
        message: ChatMessage;
      };
      setConversationId(data.conversation_id);
      setMessages((prev) => [...prev, data.message]);
      setState("idle");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Assistant request failed");
      setState("error");
    }
  }

  return (
    <section className="space-y-4 rounded-lg border border-slate-200 bg-white p-4">
      <div>
        <h2 className="text-lg font-semibold text-forest-900">Tenant assistant</h2>
        <p className="text-sm text-amber-950">{ASSISTANT_NOTICE}</p>
      </div>
      <div className="max-h-80 space-y-3 overflow-y-auto rounded-md border border-slate-100 bg-slate-50 p-3 text-sm">
        {messages.length === 0 ? (
          <p className="text-slate-600">Ask about approved organisation information, such as published announcements or emergency guidance.</p>
        ) : (
          messages.map((message, index) => (
            <div key={`${message.role}-${index}`} className={message.role === "user" ? "text-right" : "text-left"}>
              <div
                className={
                  message.role === "user"
                    ? "inline-block rounded-md bg-teal-700 px-3 py-2 text-white"
                    : "inline-block rounded-md bg-white px-3 py-2 text-slate-800 shadow-sm"
                }
              >
                <p className="whitespace-pre-wrap">{message.body}</p>
                {message.source_refs && message.source_refs.length > 0 ? (
                  <ul className="mt-2 space-y-1 text-left text-xs text-slate-600">
                    {message.source_refs.map((ref) => (
                      <li key={String(ref.content_id)}>
                        {sourceLabel(String(ref.source_type ?? ""))}: {String(ref.title ?? "")}
                      </li>
                    ))}
                  </ul>
                ) : null}
              </div>
            </div>
          ))
        )}
      </div>
      {state === "error" && error ? (
        <p className="text-sm text-red-700" role="alert">
          {error}
        </p>
      ) : null}
      <div className="flex flex-col gap-2 sm:flex-row">
        <label className="sr-only" htmlFor="tenant-assistant-question">
          Question
        </label>
        <input
          id="tenant-assistant-question"
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
          value={question}
          maxLength={2000}
          placeholder="Ask a question"
          disabled={state === "loading"}
          onChange={(event) => setQuestion(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              void send();
            }
          }}
        />
        <button
          type="button"
          className="rounded-md bg-teal-700 px-4 py-2 text-sm text-white disabled:opacity-60"
          disabled={state === "loading" || question.trim().length < 3}
          onClick={() => void send()}
        >
          {state === "loading" ? "Sending…" : "Send"}
        </button>
      </div>
    </section>
  );
}
