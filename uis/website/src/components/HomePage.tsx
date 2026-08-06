"use client";

import { useState } from "react";
import { LanguageProvider } from "@/components/providers/LanguageProvider";
import { Header } from "@/components/sections/Header";
import { Hero } from "@/components/sections/Hero";
import { WhyHealthCore } from "@/components/sections/WhyHealthCore";
import { Services } from "@/components/sections/Services";
import { Locations } from "@/components/sections/Locations";
import { Contact } from "@/components/sections/Contact";
import { Footer, QuickHelpBar } from "@/components/sections/Footer";
import { AppointmentModal } from "@/components/sections/AppointmentModal";

export function HomePage() {
  const [modalOpen, setModalOpen] = useState(false);

  return (
    <LanguageProvider>
      <a
        href="#main-content"
        className="sr-only rounded bg-blue-100 px-4 py-3 text-blue-900 focus:not-sr-only focus:absolute focus:left-2 focus:top-2"
      >
        Skip to main content
      </a>
      <Header onRequestAppointment={() => setModalOpen(true)} />
      <main id="main-content" tabIndex={-1} className="pb-24 md:pb-0">
        <Hero onRequestAppointment={() => setModalOpen(true)} />
        <WhyHealthCore />
        <Services />
        <Locations />
        <Contact />
      </main>
      <QuickHelpBar />
      <Footer />
      <AppointmentModal open={modalOpen} onClose={() => setModalOpen(false)} />
    </LanguageProvider>
  );
}
