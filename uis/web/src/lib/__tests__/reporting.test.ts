import { apiFetch, ApiHttpError } from "@/lib/apiClient";
import {
  clinicsByCountry,
  fetchLatestPipelineRun,
  fetchMonthlyClinicSupplyPerformance,
  formatReportingMonth,
  formatSupplyCost,
  monthStartFromInput,
  monthlyClinicSupplyPerformancePath,
} from "@/lib/reporting";

jest.mock("@/lib/apiClient", () => {
  const actual = jest.requireActual("@/lib/apiClient");
  return {
    ...actual,
    apiFetch: jest.fn(),
  };
});

const mockedFetch = apiFetch as jest.MockedFunction<typeof apiFetch>;

function jsonResponse(status: number, body: unknown): Response {
  const payload = {
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
    headers: { get: () => "application/json" },
  };
  return payload as unknown as Response;
}

beforeEach(() => {
  mockedFetch.mockReset();
});

describe("reporting helpers", () => {
  it("builds the KPI path with an optional month_start", () => {
    expect(monthlyClinicSupplyPerformancePath()).toBe(
      "/reporting/monthly-clinic-supply-performance",
    );
    expect(monthlyClinicSupplyPerformancePath("2026-07-01")).toBe(
      "/reporting/monthly-clinic-supply-performance?month_start=2026-07-01",
    );
  });

  it("converts a month input to a month-start date", () => {
    expect(monthStartFromInput("")).toBeNull();
    expect(monthStartFromInput("2026-07")).toBe("2026-07-01");
  });

  it("formats the reporting month for the board pack", () => {
    expect(formatReportingMonth("2026-07-01")).toBe("July 2026");
  });

  it("groups clinics by country without combining currencies", () => {
    const grouped = clinicsByCountry([
      {
        clinic_id: "1",
        country: "US",
        total_supply_cost: 10,
        supply_consumption_count: 1,
        critical_stockout_count: 0,
        expiry_risk_count: 0,
        currency: "USD",
      },
      {
        clinic_id: "2",
        country: "UK",
        total_supply_cost: 5,
        supply_consumption_count: 2,
        critical_stockout_count: 1,
        expiry_risk_count: 0,
        currency: "GBP",
      },
    ]);
    expect(grouped.US).toHaveLength(1);
    expect(grouped.UK).toHaveLength(1);
    expect(formatSupplyCost(10, "USD")).toMatch(/\$10/);
    expect(formatSupplyCost(5, "GBP")).toMatch(/£5/);
  });
});

describe("reporting fetchers", () => {
  it("GETs the KPI endpoint", async () => {
    mockedFetch.mockResolvedValue(
      jsonResponse(200, { month_start: "2026-07-01", clinics: [] }),
    );
    const result = await fetchMonthlyClinicSupplyPerformance("2026-07-01");
    expect(mockedFetch).toHaveBeenCalledWith(
      "/reporting/monthly-clinic-supply-performance?month_start=2026-07-01",
    );
    expect(result.month_start).toBe("2026-07-01");
  });

  it("returns null when the latest run is 404", async () => {
    mockedFetch.mockResolvedValue(jsonResponse(404, { detail: "No pipeline runs" }));
    await expect(fetchLatestPipelineRun()).resolves.toBeNull();
  });

  it("does not leak API detail on KPI 500", async () => {
    mockedFetch.mockResolvedValue(jsonResponse(500, { detail: "SECRET leaked" }));
    await expect(fetchMonthlyClinicSupplyPerformance()).rejects.toBeInstanceOf(ApiHttpError);
  });
});
