"use client";

import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { ErrorBanner } from "@/components/ErrorBanner";
import { SupplySelect } from "@/components/inventory/SupplySelect";
import { isAbortError, toUserMessage } from "@/lib/apiClient";
import {
  CLINIC_IDS,
  CONSUMPTION_LABELS,
  InsufficientStockError,
  createConsumption,
  getSupply,
  isClinicId,
  listSupplies,
  type ConsumptionType,
  type MedicalSupply,
} from "@/lib/inventory";

export function SupplyConsumptionForm() {
  const searchParams = useSearchParams();
  const requestedId = searchParams.get("supply_id") ?? "";
  const [supplies, setSupplies] = useState<MedicalSupply[]>([]);
  const [loadingList, setLoadingList] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [preselectNote, setPreselectNote] = useState<string | null>(null);
  const [supplyId, setSupplyId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [consumptionType, setConsumptionType] = useState<ConsumptionType>("clinical_use");
  const [clinicId, setClinicId] = useState("1");
  const [stock, setStock] = useState<MedicalSupply | null>(null);
  const [stockLoading, setStockLoading] = useState(false);
  const [stockError, setStockError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [stockConflict, setStockConflict] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const loadList = useCallback(async () => {
    setLoadingList(true);
    setLoadError(null);
    try {
      const rows = await listSupplies();
      setSupplies(rows);
      const match = rows.find((row) => String(row.id) === requestedId);
      if (requestedId && !match) {
        setPreselectNote("That medical supply could not be found. Choose one from the list.");
        setSupplyId("");
      } else if (match) {
        setPreselectNote(null);
        setSupplyId(String(match.id));
      }
    } catch (err) {
      setLoadError(toUserMessage(err));
      setSupplies([]);
    } finally {
      setLoadingList(false);
    }
  }, [requestedId]);

  useEffect(() => {
    void loadList();
  }, [loadList]);

  const refreshStock = useCallback(async (id: string) => {
    abortRef.current?.abort();
    setStock(null);
    setStockError(null);
    if (!id) {
      setStockLoading(false);
      return;
    }
    const controller = new AbortController();
    abortRef.current = controller;
    setStockLoading(true);
    try {
      const row = await getSupply(Number(id), { signal: controller.signal });
      setStock(row);
    } catch (err) {
      if (isAbortError(err) || controller.signal.aborted) return;
      setStockError(toUserMessage(err));
    } finally {
      if (!controller.signal.aborted) setStockLoading(false);
    }
  }, []);

  useEffect(() => {
    void refreshStock(supplyId);
    return () => abortRef.current?.abort();
  }, [supplyId, refreshStock]);

  const qty = Number(quantity);
  const qtyValid = Number.isInteger(qty) && qty >= 1;
  const overstock = Boolean(stock && qtyValid && qty > stock.current_stock);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (!stock || overstock || stockLoading || stockError) return;
    const clinic = Number(clinicId);
    if (!isClinicId(clinic)) {
      setFormError("Clinic must be between 1 and 12.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    setStockConflict(null);
    setSuccess(null);
    try {
      await createConsumption({
        supply_id: stock.id,
        quantity: qty,
        consumption_type: consumptionType,
        clinic_id: clinic,
      });
      setSuccess("Consumption recorded.");
      setQuantity("");
      setConsumptionType("clinical_use");
      setClinicId("1");
      setSupplyId("");
      setStock(null);
    } catch (err) {
      if (err instanceof InsufficientStockError) {
        setStockConflict(err.message);
        void refreshStock(supplyId);
      } else {
        setFormError(toUserMessage(err));
      }
    } finally {
      setSubmitting(false);
    }
  };

  const canSubmit =
    Boolean(supplyId) &&
    Boolean(stock) &&
    !stockLoading &&
    !stockError &&
    qtyValid &&
    !overstock &&
    !submitting &&
    !loadError;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Record supply consumption</h2>
        <p className="mt-1 text-sm text-slate-600">
          Record clinical use or expiry waste. Current stock is refreshed from the API before you submit.
        </p>
      </div>
      {loadError ? <ErrorBanner message={loadError} onRetry={() => void loadList()} /> : null}
      {preselectNote ? (
        <p className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-950" role="status">
          {preselectNote}
        </p>
      ) : null}
      {formError ? <ErrorBanner message={formError} /> : null}
      {success ? (
        <p className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-900" role="status">
          {success}
        </p>
      ) : null}
      <form className="max-w-xl space-y-4 rounded-xl border border-slate-200 bg-white p-5 shadow-sm" onSubmit={(e) => void onSubmit(e)}>
        {loadingList ? <p className="text-sm text-slate-500">Loading medical supplies…</p> : null}
        <SupplySelect
          supplies={supplies}
          value={supplyId}
          onChange={(next) => {
            setQuantity("");
            setStockConflict(null);
            setFormError(null);
            setSupplyId(next);
          }}
          disabled={loadingList || Boolean(loadError) || submitting}
        />
        <div className="rounded-md border border-slate-200 bg-slate-50 px-3 py-3 text-sm" aria-live="polite">
          {stockLoading ? <p className="text-slate-600">Refreshing current stock…</p> : null}
          {stockError ? (
            <p className="text-rose-800" role="alert">
              {stockError} Stock must load before you can submit.
            </p>
          ) : null}
          {stock && !stockLoading ? (
            <p className="text-slate-800">
              Current stock:{" "}
              <strong className="tabular-nums">
                {stock.current_stock} {stock.unit}
              </strong>
            </p>
          ) : null}
          {!supplyId && !stockLoading ? (
            <p className="text-slate-500">Select a medical supply to load current stock.</p>
          ) : null}
        </div>
        <fieldset>
          <legend className="text-sm text-slate-700">Consumption type</legend>
          <div className="mt-2 flex flex-col gap-2">
            {(Object.keys(CONSUMPTION_LABELS) as ConsumptionType[]).map((value) => (
              <label key={value} className="flex items-center gap-2 text-sm text-slate-800">
                <input
                  type="radio"
                  name="consumption_type"
                  value={value}
                  checked={consumptionType === value}
                  onChange={() => setConsumptionType(value)}
                  disabled={submitting}
                />
                {CONSUMPTION_LABELS[value]}
              </label>
            ))}
          </div>
        </fieldset>
        <label className="block text-sm text-slate-700" htmlFor="quantity">
          Quantity
          <input
            id="quantity"
            type="number"
            min={1}
            step={1}
            required
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2"
            value={quantity}
            onChange={(event) => {
              setQuantity(event.target.value);
              setStockConflict(null);
            }}
            disabled={submitting || !stock}
          />
        </label>
        {overstock ? (
          <p className="text-sm text-rose-800" role="alert">
            Quantity exceeds current stock ({stock?.current_stock} {stock?.unit}).
          </p>
        ) : null}
        {stockConflict ? (
          <p className="text-sm text-rose-800" role="alert">
            {stockConflict}
          </p>
        ) : null}
        <label className="block text-sm text-slate-700" htmlFor="clinic_id">
          Clinic ID
          <select
            id="clinic_id"
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2"
            value={clinicId}
            onChange={(event) => setClinicId(event.target.value)}
            disabled={submitting}
            required
          >
            {CLINIC_IDS.map((id) => (
              <option key={id} value={id}>
                Clinic {id}
              </option>
            ))}
          </select>
        </label>
        <button
          type="submit"
          disabled={!canSubmit}
          className="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
        >
          {submitting ? "Recording…" : "Record consumption"}
        </button>
      </form>
    </div>
  );
}
