"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { ErrorBanner } from "@/components/ErrorBanner";
import { StockBadge } from "@/components/inventory/StockBadge";
import { toUserMessage } from "@/lib/apiClient";
import { categoryLabel, listSupplies, type MedicalSupply } from "@/lib/inventory";

export function MedicalSuppliesList() {
  const [supplies, setSupplies] = useState<MedicalSupply[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      setSupplies(await listSupplies());
    } catch (err) {
      setError(toUserMessage(err));
      setSupplies([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Medical supplies</h2>
        <p className="mt-1 text-sm text-slate-600">
          Live catalogue stock is computed by the inventory API (deliveries minus consumption).
        </p>
      </div>
      {error ? <ErrorBanner message={error} onRetry={() => void load()} /> : null}
      <section className="overflow-x-auto rounded-xl border border-slate-200 bg-white shadow-sm">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-slate-200 bg-slate-50 text-slate-600">
            <tr>
              <th className="px-4 py-3 font-semibold">Name</th>
              <th className="px-4 py-3 font-semibold">SKU</th>
              <th className="px-4 py-3 font-semibold">Category</th>
              <th className="px-4 py-3 font-semibold">Unit</th>
              <th className="px-4 py-3 font-semibold">Country</th>
              <th className="px-4 py-3 font-semibold">Current stock</th>
              <th className="px-4 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                  Loading medical supplies…
                </td>
              </tr>
            ) : supplies.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                  No medical supplies are on file yet.
                </td>
              </tr>
            ) : (
              supplies.map((supply) => (
                <tr key={supply.id} className="border-b border-slate-100">
                  <td className="px-4 py-3 font-medium text-slate-900">{supply.name}</td>
                  <td className="px-4 py-3 text-slate-700">{supply.sku}</td>
                  <td className="px-4 py-3">
                    <span className="rounded bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                      {categoryLabel(supply.category)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-slate-700">{supply.unit}</td>
                  <td className="px-4 py-3 text-slate-700">{supply.country}</td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-semibold tabular-nums text-slate-900">
                        {supply.current_stock} {supply.unit}
                      </span>
                      <StockBadge stock={supply.current_stock} />
                    </div>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      <Link
                        href={`/backoffice/inventory/orders/inbound?supply_id=${supply.id}`}
                        className="rounded-md bg-sky-700 px-2 py-1 text-xs font-semibold text-white hover:bg-sky-800"
                      >
                        Record delivery
                      </Link>
                      <Link
                        href={`/backoffice/inventory/orders/outbound?supply_id=${supply.id}`}
                        className="rounded-md border border-slate-300 px-2 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                      >
                        Record consumption
                      </Link>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </section>
      <p className="text-sm">
        <Link className="font-semibold text-sky-800 underline" href="/backoffice/inventory/orders">
          View movement history
        </Link>
      </p>
    </div>
  );
}
