"use client";

import { useState } from "react";
import { Logo } from "@/components/ui/Logo";
import { useLanguage } from "@/components/providers/LanguageProvider";
import { navItems, t } from "@/lib/i18n";

type HeaderProps = {
  onRequestAppointment: () => void;
};

export function Header({ onRequestAppointment }: HeaderProps) {
  const { lang, setLang } = useLanguage();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-30 w-full border-b-4 border-blue-600 bg-gradient-to-b from-blue-50/80 via-white to-white">
      <div className="flex w-full items-center justify-between px-2 py-3 md:px-6 md:py-4 lg:px-10">
        <Logo />
        <nav aria-label="Main navigation" className="hidden items-center space-x-8 text-lg md:flex">
          {navItems.map((item) => (
            <a
              key={item.href}
              href={item.href}
              className="rounded font-medium hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
            >
              {t(item.label, lang)}
            </a>
          ))}
          <button
            type="button"
            onClick={onRequestAppointment}
            className="rounded font-medium hover:text-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-400"
          >
            {lang === "en" ? "Request appointment" : "Solicitar cita"}
          </button>
        </nav>
        <div className="hidden items-center space-x-2 md:flex md:space-x-3">
          <LangToggle lang={lang} setLang={setLang} />
        </div>
        <button
          type="button"
          className="rounded border border-gray-300 bg-white px-4 py-3 font-semibold text-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-400 md:hidden"
          aria-expanded={mobileOpen}
          aria-controls="mobile-nav"
          onClick={() => setMobileOpen((v) => !v)}
        >
          {lang === "en" ? "Menu" : "Menú"}
        </button>
      </div>
      {mobileOpen ? (
        <nav
          id="mobile-nav"
          aria-label="Mobile navigation"
          className="border-t border-gray-200 bg-white px-4 py-3 md:hidden"
        >
          <div className="mb-3 flex items-center space-x-2">
            <LangToggle lang={lang} setLang={setLang} />
          </div>
          <ul className="space-y-2 text-lg">
            {navItems.map((item) => (
              <li key={item.href}>
                <a
                  href={item.href}
                  className="block rounded px-2 py-2 hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  onClick={() => setMobileOpen(false)}
                >
                  {t(item.label, lang)}
                </a>
              </li>
            ))}
            <li>
              <button
                type="button"
                className="block w-full rounded px-2 py-2 text-left hover:bg-blue-50 focus:outline-none focus:ring-2 focus:ring-blue-400"
                onClick={() => {
                  setMobileOpen(false);
                  onRequestAppointment();
                }}
              >
                {lang === "en" ? "Request appointment" : "Solicitar cita"}
              </button>
            </li>
          </ul>
        </nav>
      ) : null}
    </header>
  );
}

function LangToggle({
  lang,
  setLang,
}: {
  lang: "en" | "es";
  setLang: (lang: "en" | "es") => void;
}) {
  return (
    <>
      <button
        type="button"
        onClick={() => setLang("en")}
        aria-pressed={lang === "en"}
        className={`rounded px-3 py-2 font-semibold focus:outline-none focus:ring-2 focus:ring-blue-400 ${
          lang === "en"
            ? "border border-blue-700 bg-blue-50 text-blue-700"
            : "border border-gray-300 bg-gray-50 text-gray-700"
        }`}
      >
        EN
      </button>
      <span className="text-gray-400">|</span>
      <button
        type="button"
        onClick={() => setLang("es")}
        aria-pressed={lang === "es"}
        className={`rounded px-3 py-2 font-semibold focus:outline-none focus:ring-2 focus:ring-blue-400 ${
          lang === "es"
            ? "border border-blue-700 bg-blue-50 text-blue-700"
            : "border border-gray-300 bg-gray-50 text-gray-700"
        }`}
      >
        ES
      </button>
    </>
  );
}
