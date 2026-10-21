import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MonthlyClinicSupplyReport } from "@/components/reporting/MonthlyClinicSupplyReport";
import type { MonthlyClinicSupplyPerformance, PipelineRun } from "@/lib/reporting";

jest.mock("@/lib/reporting", () => {
  const actual = jest.requireActual("@/lib/reporting");
  return {
    ...actual,
    fetchMonthlyClinicSupplyPerformance: jest.fn(),
    fetchLatestPipelineRun: jest.fn(),
  };
});

const reporting = jest.requireMock("@/lib/reporting") as {
  fetchMonthlyClinicSupplyPerformance: jest.Mock;
  fetchLatestPipelineRun: jest.Mock;
};

const populated: MonthlyClinicSupplyPerformance = {
  month_start: "2026-07-01",
  clinics: [
    {
      clinic_id: "1",
      country: "US",
      total_supply_cost: 18420.5,
      supply_consumption_count: 340,
      critical_stockout_count: 1,
      expiry_risk_count: 4,
      currency: "USD",
    },
    {
      clinic_id: "2",
      country: "UK",
      total_supply_cost: 9000,
      supply_consumption_count: 120,
      critical_stockout_count: 0,
      expiry_risk_count: 2,
      currency: "GBP",
    },
  ],
};

const latestRun: PipelineRun = {
  run_id: "run-1",
  status: "completed",
  started_at: "2026-08-01T06:00:00+00:00",
  finished_at: "2026-08-01T06:00:02+00:00",
  records_processed: 12,
  events_extracted: 80,
  events_quarantined: 1,
  window_start: "2026-07-01T00:00:00+00:00",
  window_end: "2026-08-08T00:00:00+00:00",
  error: null,
};

beforeEach(() => {
  reporting.fetchMonthlyClinicSupplyPerformance.mockReset();
  reporting.fetchLatestPipelineRun.mockReset();
  reporting.fetchLatestPipelineRun.mockResolvedValue(null);
});

describe("MonthlyClinicSupplyReport", () => {
  it("shows loading, then KPI labels, reporting month, and separate USD/GBP sections", async () => {
    reporting.fetchMonthlyClinicSupplyPerformance.mockResolvedValue(populated);
    reporting.fetchLatestPipelineRun.mockResolvedValue(latestRun);
    render(<MonthlyClinicSupplyReport />);
    expect(screen.getByText("Loading monthly clinic supply performance…")).toBeInTheDocument();
    expect(await screen.findByText("Showing July 2026")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Monthly Clinic Supply Performance" })).toBeInTheDocument();
    expect(screen.getAllByText("Supply Cost per Clinic").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Supply Consumption Volume").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Critical Stockout Frequency").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Expiry Risk Count").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "United States (USD)" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "United Kingdom (GBP)" })).toBeInTheDocument();
    expect(screen.getByText("Clinic 1")).toBeInTheDocument();
    expect(screen.getByText("Clinic 2")).toBeInTheDocument();
    expect(screen.getByText(/Latest run completed/)).toBeInTheDocument();
    expect(screen.queryByText(/27,420/)).not.toBeInTheDocument();
    expect(screen.queryByText(/grand total/i)).not.toBeInTheDocument();
  });

  it("shows an empty state when no clinic-month rows exist", async () => {
    reporting.fetchMonthlyClinicSupplyPerformance.mockResolvedValue({
      month_start: null,
      clinics: [],
    });
    render(<MonthlyClinicSupplyReport />);
    expect(
      await screen.findByText("No clinic-month supply performance has been computed yet."),
    ).toBeInTheDocument();
  });

  it("shows a failed load with retry", async () => {
    reporting.fetchMonthlyClinicSupplyPerformance.mockRejectedValue(new Error("network"));
    render(<MonthlyClinicSupplyReport />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
    reporting.fetchMonthlyClinicSupplyPerformance.mockResolvedValue({
      month_start: null,
      clinics: [],
    });
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(
      await screen.findByText("No clinic-month supply performance has been computed yet."),
    ).toBeInTheDocument();
  });
});
