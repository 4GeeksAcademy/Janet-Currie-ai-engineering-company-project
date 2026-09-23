import { Section } from "@/components/ui/Section";
import { contactCopy, t, type Lang } from "@/lib/i18n";

export function Contact({ lang }: { lang: Lang }) {
  return (
    <Section id="contact" title={t(contactCopy.title, lang)} narrow>
      <div className="flex flex-col items-center gap-6">
        <ul className="flex flex-col items-center justify-center space-y-2 text-center text-lg text-gray-800">
          {contactCopy.lines.map((line) => (
            <li key={line.value}>
              <span className="font-semibold">{t(line.label, lang)}</span>{" "}
              <a href={line.href} className="text-blue-700 underline">
                {line.value}
              </a>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-center text-lg font-bold text-red-700">
          {t(contactCopy.emergency, lang)}
        </p>
      </div>
    </Section>
  );
}
