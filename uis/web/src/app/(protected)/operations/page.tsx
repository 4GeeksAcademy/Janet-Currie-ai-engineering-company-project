"use client";

import dynamic from "next/dynamic";

const OperationsAnalytics = dynamic(
  () =>
    import("@/components/OperationsAnalytics").then((mod) => ({
      default: mod.OperationsAnalytics,
    })),
  {
    loading: () => (
      <p
        className="min-h-[24rem] rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm"
        role="status"
        aria-live="polite"
      >
        Loading operations analytics…
      </p>
    ),
  },
);

export default function OperationsPage() {
  return <OperationsAnalytics />;
}
