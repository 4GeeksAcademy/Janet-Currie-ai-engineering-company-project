"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { useLanguage } from "@/components/providers/LanguageProvider";
import { heroCopy, t } from "@/lib/i18n";

type HeroProps = {
  onRequestAppointment: () => void;
};

export function Hero({ onRequestAppointment }: HeroProps) {
  const { lang } = useLanguage();
  const [index, setIndex] = useState(0);

  useEffect(() => {
    const id = window.setInterval(() => {
      setIndex((prev) => (prev + 1) % heroCopy.taglines.length);
    }, 3500);
    return () => window.clearInterval(id);
  }, []);

  return (
    <section
      id="home"
      className="relative flex min-h-screen flex-col items-center justify-center overflow-hidden bg-white px-3 pb-10 pt-[84px] sm:py-16 md:px-0 lg:py-28"
    >
      <div className="pointer-events-none absolute inset-0 select-none" aria-hidden="true">
        <svg
          className="absolute left-1/2 top-[46%] h-auto w-[88vw] max-w-[420px] -translate-x-1/2 -translate-y-1/2 opacity-20 sm:top-[40%] sm:w-[95vw] sm:max-w-[600px] md:top-[38%] md:max-w-[760px]"
          viewBox="0 0 760 220"
          fill="none"
        >
          <ellipse cx="380" cy="110" rx="330" ry="92" fill="#3b82f6" />
        </svg>
      </div>
      <div className="relative z-10 mx-auto flex w-full max-w-xl flex-col items-center px-0 text-center sm:max-w-2xl sm:px-4 lg:max-w-4xl lg:px-0">
        <h1 className="mb-4 w-full text-2xl font-extrabold leading-tight tracking-tight text-blue-900 drop-shadow-lg sm:mb-6 sm:text-4xl md:text-6xl">
          {t(heroCopy.headline, lang)}
        </h1>
        <p
          className="mb-6 w-full max-w-md text-base font-semibold text-blue-800/90 sm:mb-10 sm:max-w-2xl sm:text-xl md:text-2xl"
          aria-live="polite"
        >
          {t(heroCopy.taglines[index], lang)}
        </p>
        <Button
          onClick={onRequestAppointment}
          className="w-full animate-pulse motion-reduce:animate-none sm:w-auto"
        >
          {t(heroCopy.cta, lang)}
        </Button>
      </div>
    </section>
  );
}
