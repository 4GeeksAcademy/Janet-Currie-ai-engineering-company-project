"use client";

import { useEffect, useRef, useState } from "react";
import { ErrorBanner } from "@/components/ErrorBanner";
import { toUserMessage } from "@/lib/apiClient";
import { askKnowledge } from "@/lib/knowledgeApi";

export function KnowledgeAssistant() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const request = useRef<AbortController | null>(null);

  useEffect(() => {
    return () => {
      request.current?.abort();
    };
  }, []);

  const submit = async () => {
    const cleaned = question.trim();
    if (!cleaned) {
      setError("Enter a policy or procedure question.");
      setAnswer(null);
      return;
    }
    if (loading) return;
    request.current?.abort();
    const controller = new AbortController();
    request.current = controller;
    setLoading(true);
    setError(null);
    try {
      const next = await askKnowledge(cleaned, controller.signal);
      if (controller.signal.aborted) return;
      setAnswer(next);
    } catch (err) {
      if (controller.signal.aborted) return;
      setAnswer(null);
      setError(toUserMessage(err));
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  };

  return (
    <section className="mx-auto max-w-3xl">
      <h2 className="text-2xl font-semibold text-slate-900">Knowledge assistant</h2>
      <p className="mt-2 text-sm text-slate-600">
        Ask a policy or procedure question. The answer comes from HealthCore&apos;s approved
        documents about insurance, appointments, referrals, and new patients.
      </p>
      <form
        className="mt-6 space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <label htmlFor="knowledge-question" className="block text-sm font-semibold text-slate-800">
          Policy or procedure question
        </label>
        <textarea
          id="knowledge-question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={5}
          disabled={loading}
          className="w-full rounded-md border border-slate-300 px-3 py-2 text-sm text-slate-900"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Ask
        </button>
      </form>
      <div className="mt-4 space-y-3" aria-live="polite">
        {loading ? (
          <p role="status" className="text-sm text-slate-600">
            Looking through the HealthCore policies…
          </p>
        ) : null}
        {error ? <ErrorBanner message={error} onRetry={() => void submit()} /> : null}
        {answer ? (
          <article className="rounded-xl border border-slate-200 bg-white p-6 text-sm leading-6 text-slate-800 shadow-sm">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Answer</h3>
            <p className="mt-2 whitespace-pre-wrap">{answer}</p>
          </article>
        ) : null}
      </div>
    </section>
  );
}
