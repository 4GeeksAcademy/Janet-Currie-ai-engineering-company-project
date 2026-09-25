"use client";

import { useState, type ReactNode } from "react";
import dynamic from "next/dynamic";
import { LanguageProvider } from "@/components/providers/LanguageProvider";
import { Header } from "@/components/sections/Header";
import { Hero } from "@/components/sections/Hero";
import type { Lang } from "@/lib/i18n";

const AppointmentModal = dynamic(
  () => import("@/components/sections/AppointmentModal").then((m) => ({ default: m.AppointmentModal })),
  { ssr: false },
);

type HomePageProps = {
  initialLang: Lang;
  mainAfterHero: ReactNode;
  afterMain: ReactNode;
};

export function HomePage({ initialLang, mainAfterHero, afterMain }: HomePageProps) {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <LanguageProvider initialLang={initialLang}>
      <a
        href="#main-content"
        className="sr-only rounded bg-blue-100 px-4 py-3 text-blue-900 focus:not-sr-only focus:absolute focus:left-2 focus:top-2"
      >
        Skip to main content
      </a>
      <Header onRequestAppointment={() => setModalOpen(true)} />
      <main id="main-content" tabIndex={-1} className="pb-24 md:pb-0">
        <Hero onRequestAppointment={() => setModalOpen(true)} />
        {mainAfterHero}
      </main>
      {afterMain}
      {modalOpen ? <AppointmentModal open={modalOpen} onClose={() => setModalOpen(false)} /> : null}
    </LanguageProvider>
  );
}
