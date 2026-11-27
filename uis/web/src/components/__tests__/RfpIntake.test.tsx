import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { RfpIntake } from "@/components/rfp/RfpIntake";
import { ApiHttpError } from "@/lib/apiClient";
import type { TicketDetail } from "@/lib/rfp";

jest.mock("@/lib/rfp", () => {
  const actual = jest.requireActual("@/lib/rfp");
  return {
    ...actual,
    uploadRfp: jest.fn(),
    getTicket: jest.fn(),
    listTickets: jest.fn(),
    reprocessTicket: jest.fn(),
  };
});

const rfp = jest.requireMock("@/lib/rfp") as {
  uploadRfp: jest.Mock;
  getTicket: jest.Mock;
  listTickets: jest.Mock;
  reprocessTicket: jest.Mock;
};

const owners = [
  {
    department_id: "revenue",
    department_name: "Revenue Cycle",
    owner_name: "Tom Callahan",
    key_aspects: ["12-month term"],
    open_questions: ["What is the budget?"],
  },
  {
    department_id: "clinical",
    department_name: "Clinical Operations",
    owner_name: "Dr. Marcus Reid",
    key_aspects: ["On-site clinic"],
    open_questions: [],
  },
  {
    department_id: "compliance",
    department_name: "Compliance and Data Governance",
    owner_name: "Claire Whitfield",
    key_aspects: ["BAA required"],
    open_questions: [],
  },
];

function completed(): TicketDetail {
  return {
    ticket_id: "t-1",
    status: "intake_complete",
    processing_state: "succeeded",
    outcome_reason_code: null,
    message: "Intake analysis is ready. This is not a proposal or an approval.",
    contains_phi: false,
    requires_compliance_review: false,
    metadata: {
      rfp_id: "r-1",
      client_name: "Meridian Manufacturing, Inc.",
      client_country: "US",
      program_type: "occupational_health",
      covered_population: 800,
      deadline: "2026-08-23",
      budget_range: null,
      departments_needed: ["revenue", "clinical", "compliance"],
      currency: "USD",
      readability: {
        flesch_reading_ease: 42,
        flesch_kincaid_grade: 12,
        gunning_fog: 14,
        word_count: 180,
        sentence_count: 10,
        character_count: 900,
        page_count: 3,
        metric_status: "ok",
      },
    },
    departments: owners,
  };
}

beforeEach(() => {
  rfp.uploadRfp.mockReset();
  rfp.getTicket.mockReset();
  rfp.listTickets.mockReset();
  rfp.reprocessTicket.mockReset();
  rfp.listTickets.mockResolvedValue([]);
});

describe("RfpIntake", () => {
  it("exposes a labeled file input and blocks a second submit", async () => {
    let finish: (value: { ticket_id: string; status: string; processing_state: string }) => void = () => undefined;
    rfp.uploadRfp.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const user = userEvent.setup();
    render(<RfpIntake />);
    const input = screen.getByLabelText("RFP PDF");
    const file = new File(["%PDF"], "request.pdf", { type: "application/pdf" });
    await user.upload(input, file);
    await user.click(screen.getByRole("button", { name: "Upload PDF" }));
    expect(screen.getByRole("button", { name: "Uploading" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Uploading" }));
    expect(rfp.uploadRfp).toHaveBeenCalledTimes(1);
    finish({ ticket_id: "t-1", status: "analyzing", processing_state: "queued" });
    expect(await screen.findByRole("status")).toHaveTextContent("Intake is still running.");
  });

  it("polls while analyzing and stops after completion and unmount", async () => {
    rfp.uploadRfp.mockResolvedValue({ ticket_id: "t-1", status: "analyzing", processing_state: "queued" });
    let resolveTicket: (value: TicketDetail) => void = () => undefined;
    rfp.getTicket.mockImplementation(
      () =>
        new Promise((resolve) => {
          resolveTicket = resolve;
        }),
    );
    const user = userEvent.setup();
    const view = render(<RfpIntake pollDelayMs={20} />);
    await user.upload(screen.getByLabelText("RFP PDF"), new File(["%PDF"], "request.pdf", { type: "application/pdf" }));
    await user.click(screen.getByRole("button", { name: "Upload PDF" }));
    await waitFor(() => expect(rfp.getTicket).toHaveBeenCalledTimes(1));
    view.unmount();
    resolveTicket({
      ...completed(),
      status: "analyzing",
      processing_state: "running",
      message: "Intake is still running.",
      metadata: null,
      departments: [],
    });
    await new Promise((resolve) => setTimeout(resolve, 40));
    expect(rfp.getTicket).toHaveBeenCalledTimes(1);
  });

  it("renders metadata and the three department owners", async () => {
    rfp.uploadRfp.mockResolvedValue({ ticket_id: "t-1", status: "analyzing", processing_state: "queued" });
    rfp.getTicket.mockResolvedValue(completed());
    const user = userEvent.setup();
    render(<RfpIntake pollDelayMs={20} />);
    await user.upload(screen.getByLabelText("RFP PDF"), new File(["%PDF"], "request.pdf", { type: "application/pdf" }));
    await user.click(screen.getByRole("button", { name: "Upload PDF" }));
    expect(await screen.findByText("Tom Callahan")).toBeInTheDocument();
    expect(screen.getByText("Dr. Marcus Reid")).toBeInTheDocument();
    expect(screen.getByText("Claire Whitfield")).toBeInTheDocument();
    expect(screen.getByText("Meridian Manufacturing, Inc.")).toBeInTheDocument();
    expect(screen.getByText(/not a completed proposal/)).toBeInTheDocument();
  });

  it("shows fixed discarded and privacy messages", async () => {
    rfp.getTicket.mockResolvedValue({
      ...completed(),
      status: "discarded",
      processing_state: "succeeded",
      outcome_reason_code: "phi_detected",
      message: "Protected information was detected. Submit a privacy-safe document so Compliance can handle it.",
      contains_phi: true,
      metadata: null,
      departments: [],
    });
    const user = userEvent.setup();
    render(<RfpIntake pollDelayMs={20} />);
    await user.upload(screen.getByLabelText("RFP PDF"), new File(["%PDF"], "request.pdf", { type: "application/pdf" }));
    rfp.uploadRfp.mockResolvedValue({ ticket_id: "t-phi", status: "analyzing", processing_state: "queued" });
    await user.click(screen.getByRole("button", { name: "Upload PDF" }));
    expect(
      await screen.findByText(
        "Protected information was detected. Submit a privacy-safe document so Compliance can handle it.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByText(/not_an_rfp/)).not.toBeInTheDocument();
  });

  it("does not render a raw server error", async () => {
    rfp.uploadRfp.mockRejectedValue(new ApiHttpError("Traceback: patient secret and stack", 500));
    const user = userEvent.setup();
    render(<RfpIntake />);
    await user.upload(screen.getByLabelText("RFP PDF"), new File(["%PDF"], "request.pdf", { type: "application/pdf" }));
    await user.click(screen.getByRole("button", { name: "Upload PDF" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Something went wrong on our side. Please try again.");
    expect(alert).not.toHaveTextContent("Traceback");
    expect(alert).not.toHaveTextContent("patient secret");
  });

  it("shows a broker failure on the same ticket", async () => {
    rfp.uploadRfp.mockResolvedValue({ ticket_id: "t-fail", status: "analyzing", processing_state: "failed" });
    rfp.getTicket.mockResolvedValue({
      ticket_id: "t-fail",
      status: "analyzing",
      processing_state: "failed",
      outcome_reason_code: "processing_failed",
      message: "Intake did not finish. You can retry this ticket.",
      contains_phi: false,
      requires_compliance_review: false,
      metadata: null,
      departments: [],
    });
    const user = userEvent.setup();
    render(<RfpIntake pollDelayMs={20} />);
    await user.upload(screen.getByLabelText("RFP PDF"), new File(["%PDF"], "request.pdf", { type: "application/pdf" }));
    await user.click(screen.getByRole("button", { name: "Upload PDF" }));
    expect(await screen.findByText("Intake did not finish. You can retry this ticket.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry intake" })).toBeInTheDocument();
    expect(screen.queryByText(/503/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Traceback/)).not.toBeInTheDocument();
  });
});
