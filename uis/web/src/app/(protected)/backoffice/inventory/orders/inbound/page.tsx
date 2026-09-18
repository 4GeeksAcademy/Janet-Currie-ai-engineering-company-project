import { Suspense } from "react";
import { SupplyDeliveryForm } from "@/components/inventory/SupplyDeliveryForm";

export default function SupplyDeliveryPage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-600">Loading delivery form…</p>}>
      <SupplyDeliveryForm />
    </Suspense>
  );
}
