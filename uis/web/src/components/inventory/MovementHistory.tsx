"use client";

import Link from "next/link";
import { ErrorBanner } from "@/components/ErrorBanner";
import {
  formatInventoryDate,
  listMovements,
  movementTypeLabel,
} from "@/lib/inventory";
import { useAsyncResource } from "@/lib/useAsyncResource";

export function MovementHistory() {
  const { data, error, loading, reload } = useAsyncResource(listMovements);
  const rows = data ?? [];

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Inventory movement history</h2>
        <p className="mt-1 text-sm text-slate-600">
          Read-only deliveries and consumption events, newest first.
        </p>
      </div>
      {error ? <ErrorBanner message={error} onRetry={() => void reload()} /> : null}
      <section className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-3 font-semibold">Medical supply</th>
              <th className="px-4 py-3 font-semibold">Quantity</th>
              <th className="px-4 py-3 font-semibold">Type</th>
              <th className="px-4 py-3 font-semibold">Date</th>
              <th className="px-4 py-3 font-semibold">Recorded by (user_uuid)</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  Loading movement history…
                </td>
              </tr>
            ) : rows.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  No inventory movements have been recorded yet.
                </td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={`${row.kind}-${row.id}`} className="border-b border-slate-100">
                  <td className="px-4 py-3 font-medium text-slate-900">{row.supply.name}</td>
                  <td className="px-4 py-3 tabular-nums text-slate-700">
                    {row.quantity} {row.supply.unit}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        row.kind === "inbound"
                          ? "rounded-full bg-sky-100 px-2 py-1 text-xs font-semibold text-sky-900"
                          : "rounded-full bg-slate-200 px-2 py-1 text-xs font-semibold text-slate-800"
                      }
                    >
                      {movementTypeLabel(row)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{formatInventoryDate(row.created_at)}</td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-700">{row.user_uuid}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
      <p className="text-sm">
        <Link className="font-semibold text-sky-800 underline" href="/backoffice/inventory/products">
          Back to medical supplies
        </Link>
      </p>
    </div>
  );
}
