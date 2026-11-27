import { apiFetch, parseError, readJson } from "@/lib/apiClient";

export const MAX_PDF_BYTES = 10 * 1024 * 1024;

export type TicketAccepted = {
  ticket_id: string;
  status: string;
  processing_state: string;
};

export type TicketSummary = TicketAccepted & {
  client_name?: string | null;
  client_country?: string | null;
  program_type?: string | null;
  outcome_reason_code?: string | null;
  created_at?: string;
  updated_at?: string;
};

export type DepartmentView = {
  department_id: string;
  department_name: string;
  owner_name: string;
  key_aspects: string[];
  open_questions: string[];
};

export type TicketDetail = {
  ticket_id: string;
  status: string;
  processing_state: string;
  outcome_reason_code: string | null;
  message: string;
  contains_phi: boolean;
  requires_compliance_review: boolean;
  metadata: {
    rfp_id: string;
    client_name: string | null;
    client_country: string | null;
    program_type: string | null;
    covered_population: number | null;
    deadline: string | null;
    budget_range: string | null;
    departments_needed: string[];
    currency: string | null;
    readability: {
      flesch_reading_ease: number | null;
      flesch_kincaid_grade: number | null;
      gunning_fog: number | null;
      word_count: number | null;
      sentence_count: number | null;
      character_count: number | null;
      page_count: number | null;
      metric_status: string | null;
    };
  } | null;
  departments: DepartmentView[];
};

export function isTerminal(ticket: { status: string; processing_state: string }): boolean {
  return (
    ticket.status === "intake_complete" ||
    ticket.status === "discarded" ||
    ticket.processing_state === "failed"
  );
}

export function messageForAccepted(processingState: string): string {
  if (processingState === "failed") return "Intake did not finish. You can retry this ticket.";
  return "Intake is still running.";
}

export async function uploadRfp(file: File): Promise<TicketAccepted> {
  const body = new FormData();
  body.append("file", file);
  const response = await apiFetch("/rfp/tickets", { method: "POST", body });
  if (response.status === 503) {
    const accepted = await readJson<TicketAccepted>(response);
    if (accepted.ticket_id) return accepted;
  }
  if (!response.ok) {
    await parseError(response);
  }
  return readJson<TicketAccepted>(response);
}

export async function listTickets(): Promise<TicketSummary[]> {
  const response = await apiFetch("/rfp/tickets");
  if (!response.ok) {
    await parseError(response);
  }
  const payload = await readJson<{ items: TicketSummary[] }>(response);
  return payload.items;
}

export async function getTicket(ticketId: string): Promise<TicketDetail> {
  const response = await apiFetch(`/rfp/tickets/${encodeURIComponent(ticketId)}`);
  if (!response.ok) {
    await parseError(response);
  }
  return readJson<TicketDetail>(response);
}

export async function reprocessTicket(ticketId: string): Promise<TicketAccepted> {
  const response = await apiFetch(`/rfp/tickets/${encodeURIComponent(ticketId)}/reprocess`, {
    method: "POST",
  });
  if (!response.ok) {
    await parseError(response);
  }
  return readJson<TicketAccepted>(response);
}
