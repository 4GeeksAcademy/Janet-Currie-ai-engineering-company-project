import { Suspense } from "react";
import { SupplyConsumptionForm } from "@/components/inventory/SupplyConsumptionForm";

export default function SupplyConsumptionPage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-600">Loading consumption form…</p>}>
      <SupplyConsumptionForm />
    </Suspense>
  );
}
