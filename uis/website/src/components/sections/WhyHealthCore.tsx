"use client";

import { Card } from "@/components/ui/Card";
import { Section } from "@/components/ui/Section";
import { useLanguage } from "@/components/providers/LanguageProvider";
import { t, whyHealthCore } from "@/lib/i18n";

export function WhyHealthCore() {
  const { lang } = useLanguage();

  return (
    <Section id="why-healthcore" title={t(whyHealthCore.title, lang)}>
      <div className="grid gap-6 md:grid-cols-2 md:gap-8">
        {whyHealthCore.cards.map((card) => (
          <Card key={card.title.en} eyebrow={t(card.title, lang)}>
            <ul className="space-y-3 text-gray-800">
              {card.items.map((item) => (
                <li key={item.en} className="flex items-start gap-2">
                  <span aria-hidden="true" className="mt-0.5">
                    ✓
                  </span>
                  <span>{t(item, lang)}</span>
                </li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </Section>
  );
}
