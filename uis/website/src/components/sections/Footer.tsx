"use client";

import { useLanguage } from "@/components/providers/LanguageProvider";
import { contactCopy, t } from "@/lib/i18n";

export function Footer() {
  return (
    <footer className="mt-12 bg-blue-900 py-8 text-white">
      <div className="mx-auto flex max-w-6xl flex-col items-center justify-between px-4 md:flex-row md:px-8">
        <span className="mb-4 block text-lg md:mb-0">
          © 2025 HealthCore. All rights reserved.
        </span>
        <div className="flex space-x-6">
          <a
            href="https://linkedin.com/company/healthcore"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-blue-200"
          >
            LinkedIn
          </a>
          <a
            href="https://facebook.com/healthcore"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-blue-200"
          >
            Facebook
          </a>
          <a
            href="https://instagram.com/healthcore"
            target="_blank"
            rel="noopener noreferrer"
            className="hover:text-blue-200"
          >
            Instagram
          </a>
        </div>
      </div>
    </footer>
  );
}

export function QuickHelpBar() {
  const { lang } = useLanguage();

  return (
    <aside
      className="fixed inset-x-0 bottom-0 z-40 border-t border-blue-700 bg-blue-900 text-white md:hidden"
      aria-label="Quick help bar"
    >
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 max-[360px]:flex-col max-[360px]:items-stretch max-[360px]:gap-2">
        <p className="text-base font-semibold leading-snug">
          {t(contactCopy.quickHelp, lang)}
        </p>
        <a
          href="tel:+15123408800"
          className="inline-flex shrink-0 items-center justify-center rounded bg-white px-4 py-3 text-base font-bold text-blue-900 focus:outline-none focus:ring-2 focus:ring-blue-200 max-[360px]:w-full"
        >
          {t(contactCopy.callNow, lang)}
        </a>
      </div>
    </aside>
  );
}
