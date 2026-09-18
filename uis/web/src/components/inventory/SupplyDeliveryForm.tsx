"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";
import { useSearchParams } from "next/navigation";
import { ErrorBanner } from "@/components/ErrorBanner";
import { SupplySelect } from "@/components/inventory/SupplySelect";
import { toUserMessage } from "@/lib/apiClient";
import { CLINIC_IDS, createDelivery, isClinicId, listSupplies, type MedicalSupply } from "@/lib/inventory";

export function SupplyDeliveryForm() {
  const searchParams = useSearchParams();
  const requestedId = searchParams.get("supply_id") ?? "";
  const [supplies, setSupplies] = useState<MedicalSupply[]>([]);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [preselectNote, setPreselectNote] = useState<string | null>(null);
  const [supplyId, setSupplyId] = useState("");
  const [quantity, setQuantity] = useState("");
  const [vendorName, setVendorName] = useState("");
  const [clinicId, setClinicId] = useState("1");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
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
      setLoading(false);
    }
  }, [requestedId]);

  useEffect(() => {
    void load();
  }, [load]);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    const qty = Number(quantity);
    if (!Number.isInteger(qty) || qty < 1) {
      setFormError("Enter a positive whole-number quantity.");
      return;
    }
    const clinic = Number(clinicId);
    if (!isClinicId(clinic)) {
      setFormError("Clinic must be between 1 and 12.");
      return;
    }
    setSubmitting(true);
    setFormError(null);
    setSuccess(null);
    try {
      await createDelivery({
        supply_id: Number(supplyId),
        quantity: qty,
        vendor_name: vendorName.trim(),
        clinic_id: clinic,
      });
      setSuccess("Delivery recorded.");
      setQuantity("");
      setVendorName("");
      setClinicId("1");
      setSupplyId(requestedId && supplies.some((row) => String(row.id) === requestedId) ? requestedId : "");
    } catch (err) {
      setFormError(toUserMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const blocked = loading || Boolean(loadError) || submitting || supplies.length === 0;

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-semibold text-slate-900">Record supply delivery</h2>
        <p className="mt-1 text-sm text-slate-600">
          Confirm a vendor shipment received at a clinic. Staff identity is taken from your signed-in account.
        </p>
      </div>
      {loadError ? <ErrorBanner message={loadError} onRetry={() => void load()} /> : null}
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
        {loading ? <p className="text-sm text-slate-500">Loading medical supplies…</p> : null}
        <SupplySelect
          supplies={supplies}
          value={supplyId}
          onChange={setSupplyId}
          disabled={loading || Boolean(loadError) || submitting}
        />
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
            onChange={(event) => setQuantity(event.target.value)}
            disabled={submitting}
          />
        </label>
        <label className="block text-sm text-slate-700" htmlFor="vendor_name">
          Vendor name
          <input
            id="vendor_name"
            type="text"
            required
            className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2"
            value={vendorName}
            onChange={(event) => setVendorName(event.target.value)}
            disabled={submitting}
          />
        </label>
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
          disabled={blocked || !supplyId}
          className="rounded-md bg-sky-700 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-800 disabled:opacity-50"
        >
          {submitting ? "Recording…" : "Record delivery"}
        </button>
      </form>
    </div>
  );
}
