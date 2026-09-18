import { stockStatus, stockStatusLabel } from "@/lib/inventory";

export function StockBadge({ stock }: { stock: number }) {
  const level = stockStatus(stock);
  const label = stockStatusLabel(level);
  const className =
    level === "out"
      ? "bg-rose-100 text-rose-900"
      : level === "low"
        ? "bg-amber-100 text-amber-950"
        : "bg-emerald-100 text-emerald-900";
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-1 text-xs font-semibold ${className}`}>
      {label}
    </span>
  );
}
