"use client";

import type { Lang } from "@/lib/i18n";

type LangToggleProps = {
  lang: Lang;
  setLang: (lang: Lang) => void;
};

export function LangToggle({ lang, setLang }: LangToggleProps) {
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
