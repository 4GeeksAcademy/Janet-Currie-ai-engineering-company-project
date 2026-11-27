"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { toUserMessage } from "@/lib/apiClient";
import {
  DepartmentView,
  MAX_PDF_BYTES,
  TicketDetail,
  TicketSummary,
  getTicket,
  isTerminal,
  listTickets,
  messageForAccepted,
  reprocessTicket,
  uploadRfp,
} from "@/lib/rfp";

type Props = { pollDelayMs?: number };

export function RfpIntake({ pollDelayMs = 1000 }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tickets, setTickets] = useState<TicketSummary[]>([]);
  const [detail, setDetail] = useState<TicketDetail | null>(null);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [pollToken, setPollToken] = useState(0);
  const busy = useRef(false);

  useEffect(() => {
    let cancelled = false;
    listTickets()
      .then((items) => {
        if (!cancelled) setTickets(items);
      })
      .catch((err: unknown) => {
        if (!cancelled) setError(toUserMessage(err));
      });
    return () => {
      cancelled = true;
    };
  }, [pollToken]);

  useEffect(() => {
    if (!activeId) return;
    let cancelled = false;
    let timer = 0;
    let delay = pollDelayMs;

    const tick = async () => {
      try {
        const next = await getTicket(activeId);
        if (cancelled) return;
        setDetail(next);
        if (isTerminal(next)) return;
        delay = Math.min(delay * 2, 8000);
        timer = window.setTimeout(() => {
          void tick();
        }, delay);
      } catch (err: unknown) {
        if (!cancelled) setError(toUserMessage(err));
      }
    };

    timer = window.setTimeout(() => {
      void tick();
    }, delay);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [activeId, pollDelayMs, pollToken]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (busy.current) return;
    if (!file) {
      setError("Choose a PDF to upload.");
      return;
    }
    if (file.size > MAX_PDF_BYTES) {
      setError("That PDF is too large. The limit is 10 MB.");
      return;
    }
    busy.current = true;
    setUploading(true);
    setError(null);
    try {
      const accepted = await uploadRfp(file);
      setActiveId(accepted.ticket_id);
      setDetail({
        ticket_id: accepted.ticket_id,
        status: accepted.status,
        processing_state: accepted.processing_state,
        outcome_reason_code: null,
        message: messageForAccepted(accepted.processing_state),
        contains_phi: false,
        requires_compliance_review: false,
        metadata: null,
        departments: [],
      });
      setPollToken((value) => value + 1);
      setFile(null);
    } catch (err: unknown) {
      setError(toUserMessage(err));
    } finally {
      busy.current = false;
      setUploading(false);
    }
  }

  async function onRetry() {
    if (!detail || busy.current) return;
    busy.current = true;
    setError(null);
    try {
      const accepted = await reprocessTicket(detail.ticket_id);
      setActiveId(accepted.ticket_id);
      setDetail({
        ...detail,
        status: accepted.status,
        processing_state: accepted.processing_state,
        message: messageForAccepted(accepted.processing_state),
        metadata: null,
        departments: [],
      });
      setPollToken((value) => value + 1);
    } catch (err: unknown) {
      setError(toUserMessage(err));
    } finally {
      busy.current = false;
    }
  }

  return (
    <section className="mx-auto max-w-5xl space-y-8">
      <header className="space-y-2">
        <h2 className="text-2xl font-semibold text-slate-900">RFP intake</h2>
        <p className="text-sm text-slate-600">
          Upload an institutional PDF. This result is intake analysis. It is not a completed proposal or an approval.
        </p>
      </header>

      <form onSubmit={onSubmit} className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="space-y-2">
          <label htmlFor="rfp-file" className="block text-sm font-medium text-slate-800">
            RFP PDF
          </label>
          <input
            id="rfp-file"
            type="file"
            accept="application/pdf,.pdf"
            className="block w-full text-sm text-slate-700 file:mr-4 file:rounded-md file:border-0 file:bg-blue-600 file:px-3 file:py-2 file:text-sm file:font-semibold file:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
          <p className="text-sm text-slate-600">PDF only. Maximum size 10 MB.</p>
        </div>
        <button
          type="submit"
          disabled={uploading}
          className="rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-slate-300"
        >
          {uploading ? "Uploading" : "Upload PDF"}
        </button>
      </form>

      {error ? (
        <p role="alert" className="rounded-md border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800">
          {error}
        </p>
      ) : null}

      {detail ? <TicketPanel detail={detail} onRetry={() => void onRetry()} /> : null}

      <div className="space-y-3">
        <h3 className="text-lg font-semibold text-slate-900">Tickets</h3>
        {tickets.length === 0 ? (
          <p className="text-sm text-slate-600">No intake tickets yet.</p>
        ) : (
          <ul className="divide-y divide-slate-200 rounded-xl border border-slate-200 bg-white">
            {tickets.map((ticket) => (
              <li key={ticket.ticket_id}>
                <button
                  type="button"
                  className="flex w-full items-center justify-between px-4 py-3 text-left text-sm hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-blue-700"
                  onClick={() => {
                    setActiveId(ticket.ticket_id);
                    setPollToken((value) => value + 1);
                  }}
                >
                  <span className="font-medium text-slate-800">{ticket.client_name || ticket.ticket_id}</span>
                  <span className="text-slate-600">{ticket.status}</span>
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}

function TicketPanel({ detail, onRetry }: { detail: TicketDetail; onRetry: () => void }) {
  const running = !isTerminal(detail);
  return (
    <article className="space-y-4 rounded-xl border border-slate-200 bg-white p-6 shadow-sm" aria-live="polite">
      <p role="status" className="text-sm font-medium text-slate-800">
        {detail.message}
      </p>
      {running ? <p className="text-sm text-slate-600">Status: {detail.status}. Queue: {detail.processing_state}.</p> : null}
      {detail.processing_state === "failed" ? (
        <button
          type="button"
          onClick={onRetry}
          className="rounded-md border border-blue-700 px-3 py-2 text-sm font-semibold text-blue-800"
        >
          Retry intake
        </button>
      ) : null}
      {detail.metadata ? (
        <dl className="grid gap-3 text-sm text-slate-800 sm:grid-cols-2">
          <div>
            <dt className="font-semibold">Client</dt>
            <dd>{detail.metadata.client_name || "Not stated"}</dd>
          </div>
          <div>
            <dt className="font-semibold">Country</dt>
            <dd>{detail.metadata.client_country || "Not stated"}</dd>
          </div>
          <div>
            <dt className="font-semibold">Program</dt>
            <dd>{detail.metadata.program_type?.replaceAll("_", " ") || "Not stated"}</dd>
          </div>
          <div>
            <dt className="font-semibold">Currency</dt>
            <dd>{detail.metadata.currency || "Not stated"}</dd>
          </div>
          <div>
            <dt className="font-semibold">Population</dt>
            <dd>{detail.metadata.covered_population ?? "Not stated"}</dd>
          </div>
          <div>
            <dt className="font-semibold">Proposal deadline</dt>
            <dd>{detail.metadata.deadline || "Not stated"}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="font-semibold">Readability</dt>
            <dd>
              Flesch {detail.metadata.readability.flesch_reading_ease ?? "n/a"}, grade{" "}
              {detail.metadata.readability.flesch_kincaid_grade ?? "n/a"}, fog{" "}
              {detail.metadata.readability.gunning_fog ?? "n/a"}. {detail.metadata.readability.word_count ?? 0} words,{" "}
              {detail.metadata.readability.page_count ?? 0} pages.
            </dd>
          </div>
        </dl>
      ) : null}
      <div className="grid gap-4 md:grid-cols-3">
        {detail.departments.map((department) => (
          <DepartmentCard key={department.department_id} department={department} />
        ))}
      </div>
    </article>
  );
}

function DepartmentCard({ department }: { department: DepartmentView }) {
  return (
    <section className="rounded-lg border border-slate-200 bg-blue-50 p-4">
      <h3 className="text-sm font-semibold text-slate-900">{department.department_name}</h3>
      <p className="mt-1 text-sm text-slate-700">{department.owner_name}</p>
      <h4 className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-600">Key aspects</h4>
      <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-slate-800">
        {department.key_aspects.map((aspect) => (
          <li key={aspect}>{aspect}</li>
        ))}
      </ul>
      <h4 className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-600">Open questions</h4>
      <ul className="mt-1 list-disc space-y-1 pl-4 text-sm text-slate-800">
        {department.open_questions.length === 0 ? <li>None recorded.</li> : null}
        {department.open_questions.map((question) => (
          <li key={question}>{question}</li>
        ))}
      </ul>
    </section>
  );
}
