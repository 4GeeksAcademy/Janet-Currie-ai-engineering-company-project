"use client";

import dynamic from "next/dynamic";

const IncidentAnalyzer = dynamic(
  () =>
    import("@/components/IncidentAnalyzer").then((mod) => ({
      default: mod.IncidentAnalyzer,
    })),
  {
    loading: () => (
      <p
        className="min-h-[24rem] rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-600 shadow-sm"
        role="status"
        aria-live="polite"
      >
        Loading incident analyzer…
      </p>
    ),
  },
);

export default function IncidentsPage() {
  return <IncidentAnalyzer />;
}
