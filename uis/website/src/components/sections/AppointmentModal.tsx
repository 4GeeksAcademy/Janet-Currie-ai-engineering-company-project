"use client";

import { EnquiryForm } from "@/components/forms/EnquiryForm";
import { useLanguage } from "@/components/providers/LanguageProvider";

type AppointmentModalProps = {
  open: boolean;
  onClose: () => void;
};

export function AppointmentModal({ open, onClose }: AppointmentModalProps) {
  const { lang } = useLanguage();

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50"
      role="dialog"
      aria-modal="true"
      aria-labelledby="appointment-modal-title"
    >
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/65"
        aria-label="Close dialog backdrop"
        onClick={onClose}
      />
      <section className="relative z-10 h-full w-full overflow-y-auto px-3 py-4 md:px-6 md:py-8">
        <div className="mx-auto w-full max-w-5xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl">
          <div className="flex items-center justify-between gap-4 border-b border-slate-200 bg-slate-50 px-4 py-3 md:px-6 md:py-4">
            <h2 id="appointment-modal-title" className="text-lg font-bold text-blue-900 md:text-2xl">
              {lang === "en" ? "Request an Appointment" : "Solicitar una cita"}
            </h2>
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-slate-800 focus:outline-none focus:ring-2 focus:ring-blue-400 md:text-base"
            >
              {lang === "en" ? "Close" : "Cerrar"}
            </button>
          </div>
          <div className="max-h-[78vh] overflow-y-auto p-4 md:p-6">
            <EnquiryForm />
          </div>
        </div>
      </section>
    </div>
  );
}
