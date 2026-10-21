import { apiFetch, parseError, readJson } from "@/lib/apiClient";

export type ClinicSupplyKpi = {
  clinic_id: string;
  country: string;
  total_supply_cost: number;
  supply_consumption_count: number;
  critical_stockout_count: number;
  expiry_risk_count: number;
  currency: string;
};

export type MonthlyClinicSupplyPerformance = {
  month_start: string | null;
  clinics: ClinicSupplyKpi[];
};

export type PipelineRun = {
  run_id: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  records_processed: number;
  events_extracted: number;
  events_quarantined: number;
  window_start: string;
  window_end: string;
  error: string | null;
};

export function monthlyClinicSupplyPerformancePath(monthStart?: string | null): string {
  const base = "/reporting/monthly-clinic-supply-performance";
  if (!monthStart) return base;
  return `${base}?month_start=${encodeURIComponent(monthStart)}`;
}

export function monthStartFromInput(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) return null;
  const match = /^(\d{4})-(\d{2})$/.exec(trimmed);
  if (!match) return null;
  return `${match[1]}-${match[2]}-01`;
}

export function monthInputValue(monthStart: string | null): string {
  if (!monthStart) return "";
  return monthStart.slice(0, 7);
}

export function formatReportingMonth(monthStart: string | null): string {
  if (!monthStart) return "";
  const [yearText, monthText] = monthStart.split("-");
  const year = Number(yearText);
  const month = Number(monthText);
  if (!year || !month) return monthStart;
  return new Intl.DateTimeFormat("en-GB", {
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, 1)));
}

export function formatSupplyCost(value: number, currency: string): string {
  const code = currency === "GBP" ? "GBP" : "USD";
  return new Intl.NumberFormat(code === "GBP" ? "en-GB" : "en-US", {
    style: "currency",
    currency: code,
  }).format(value);
}

export function clinicsByCountry(clinics: ClinicSupplyKpi[]): {
  US: ClinicSupplyKpi[];
  UK: ClinicSupplyKpi[];
} {
  return {
    US: clinics.filter((row) => row.country === "US"),
    UK: clinics.filter((row) => row.country === "UK"),
  };
}

export async function fetchMonthlyClinicSupplyPerformance(
  monthStart?: string | null,
): Promise<MonthlyClinicSupplyPerformance> {
  const response = await apiFetch(monthlyClinicSupplyPerformancePath(monthStart));
  if (!response.ok) await parseError(response);
  return readJson<MonthlyClinicSupplyPerformance>(response);
}

export async function fetchLatestPipelineRun(): Promise<PipelineRun | null> {
  const response = await apiFetch("/reporting/pipeline-runs/latest");
  if (response.status === 404) return null;
  if (!response.ok) await parseError(response);
  return readJson<PipelineRun>(response);
}
