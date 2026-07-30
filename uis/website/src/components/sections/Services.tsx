"use client";

import { Card } from "@/components/ui/Card";
import { Section } from "@/components/ui/Section";
import { useLanguage } from "@/components/providers/LanguageProvider";
import { services, t } from "@/lib/i18n";

export function Services() {
  const { lang } = useLanguage();

  return (
    <Section id="services" title={t(services.title, lang)}>
      <div className="grid gap-6 md:grid-cols-3 md:gap-8">
        {services.items.map((service) => (
          <Card key={service.title.en} title={t(service.title, lang)}>
            <ul className="mx-auto w-fit list-outside list-disc space-y-1 pl-5 text-left text-gray-800">
              {service.bullets.map((bullet) => (
                <li key={bullet.en}>{t(bullet, lang)}</li>
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </Section>
  );
}
