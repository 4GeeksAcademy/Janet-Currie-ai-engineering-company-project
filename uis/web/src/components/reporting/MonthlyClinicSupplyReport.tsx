"use client";

import { useCallback, useState } from "react";
import { ErrorBanner } from "@/components/ErrorBanner";
import {
  clinicsByCountry,
  fetchLatestPipelineRun,
  fetchMonthlyClinicSupplyPerformance,
  formatReportingMonth,
  formatSupplyCost,
  monthStartFromInput,
  type ClinicSupplyKpi,
  type PipelineRun,
} from "@/lib/reporting";
import { useAsyncResource } from "@/lib/useAsyncResource";

const KPI_COLUMNS = [
  { key: "total_supply_cost", label: "Supply Cost per Clinic" },
  { key: "supply_consumption_count", label: "Supply Consumption Volume" },
  { key: "critical_stockout_count", label: "Critical Stockout Frequency" },
  { key: "expiry_risk_count", label: "Expiry Risk Count" },
] as const;

function ClinicTable({
  heading,
  currencyNote,
  rows,
}: {
  heading: string;
  currencyNote: string;
  rows: ClinicSupplyKpi[];
}) {
  return (
    <section className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-200 bg-slate-50 px-4 py-3">
        <h3 className="text-lg font-semibold text-slate-900">{heading}</h3>
        <p className="text-sm text-slate-600">{currencyNote}</p>
      </div>
      <table className="min-w-full text-left text-sm">
        <thead className="border-b border-slate-200 text-slate-600">
          <tr>
            <th className="px-4 py-3 font-semibold">Clinic</th>
            {KPI_COLUMNS.map((column) => (
              <th key={column.key} className="px-4 py-3 font-semibold">
                {column.label}
              </th>
            ))}
            <th className="px-4 py-3 font-semibold">Currency</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 ? (
            <tr>
              <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                No clinics reported for this country in the selected month.
              </td>
            </tr>
          ) : (
            rows.map((row) => (
              <tr key={`${row.country}-${row.clinic_id}`} className="border-b border-slate-100">
                <td className="px-4 py-3 font-medium text-slate-900">Clinic {row.clinic_id}</td>
                <td className="px-4 py-3 tabular-nums text-slate-800">
                  {formatSupplyCost(row.total_supply_cost, row.currency)}
                </td>
                <td className="px-4 py-3 tabular-nums text-slate-800">{row.supply_consumption_count}</td>
                <td className="px-4 py-3 tabular-nums text-slate-800">{row.critical_stockout_count}</td>
                <td className="px-4 py-3 tabular-nums text-slate-800">{row.expiry_risk_count}</td>
                <td className="px-4 py-3 text-slate-800">{row.currency}</td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </section>
  );
}

function latestRunCopy(run: PipelineRun | null, loading: boolean, error: string | null): string {
  if (loading) return "Checking latest pipeline run…";
  if (error) return "The latest pipeline run status could not be loaded.";
  if (!run) return "No pipeline run recorded yet.";
  const finished = run.finished_at ? ` Finished ${run.finished_at}.` : "";
  return `Latest run ${run.status}: ${run.records_processed} clinic-month rows, ${run.events_extracted} events extracted, ${run.events_quarantined} quarantined.${finished}`;
}

export function MonthlyClinicSupplyReport() {
  const [monthInput, setMonthInput] = useState("");
  const monthStart = monthStartFromInput(monthInput);

  const loadReport = useCallback(
    () => fetchMonthlyClinicSupplyPerformance(monthStart),
    [monthStart],
  );
  const loadRun = useCallback(() => fetchLatestPipelineRun(), []);

  const { data, error, loading, reload } = useAsyncResource(loadReport);
  const latestRun = useAsyncResource(loadRun);

  const clinics = data?.clinics ?? [];
  const grouped = clinicsByCountry(clinics);
  const reportingMonth = formatReportingMonth(data?.month_start ?? null);
  const empty = !loading && !error && clinics.length === 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Monthly Clinic Supply Performance</h2>
        <p className="mt-1 text-sm text-slate-600">
          Board pack for Dr. Okonkwo and Claire: one row per clinic for the reporting month. United
          States (USD) and United Kingdom (GBP) are shown separately and are never combined.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-4">
        <label className="text-sm text-slate-700">
          Reporting month
          <input
            type="month"
            value={monthInput}
            onChange={(event) => setMonthInput(event.target.value)}
            className="mt-1 block rounded-md border border-slate-300 px-3 py-2 text-slate-900"
          />
        </label>
        <p className="text-sm text-slate-600" data-testid="reporting-month">
          {loading
            ? "Loading month…"
            : reportingMonth
              ? `Showing ${reportingMonth}`
              : "No reporting month computed yet"}
        </p>
      </div>

      <p className="text-sm text-slate-600" role="status">
        {latestRunCopy(latestRun.data, latestRun.loading, latestRun.error)}
      </p>

      {error ? <ErrorBanner message={error} onRetry={() => void reload()} /> : null}

      {loading ? (
        <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm" role="status">
          Loading monthly clinic supply performance…
        </p>
      ) : null}

      {empty ? (
        <p className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm">
          No clinic-month supply performance has been computed yet.
        </p>
      ) : null}

      {!loading && !error && clinics.length > 0 ? (
        <div className="space-y-6">
          <ClinicTable
            heading="United States (USD)"
            currencyNote="Amounts in US dollars. Not added to UK figures."
            rows={grouped.US}
          />
          <ClinicTable
            heading="United Kingdom (GBP)"
            currencyNote="Amounts in pounds sterling. Not added to US figures."
            rows={grouped.UK}
          />
        </div>
      ) : null}
    </div>
  );
}
