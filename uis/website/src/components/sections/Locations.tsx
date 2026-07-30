"use client";

import { Section } from "@/components/ui/Section";
import { useLanguage } from "@/components/providers/LanguageProvider";
import { clinics } from "@/lib/locations";

export function Locations() {
  const { lang } = useLanguage();
  const title = lang === "en" ? "Our US Locations" : "Nuestras ubicaciones en EE. UU.";

  return (
    <Section id="locations" title={title}>
      <div className="space-y-4 md:hidden">
        {clinics.map((clinic) => (
          <article
            key={clinic.name}
            className="rounded-xl border border-gray-200 bg-white p-6 shadow-lg transition-shadow duration-200 hover:shadow-2xl"
          >
            <h3 className="text-xl font-semibold text-blue-700">{clinic.name}</h3>
            <p className="mt-2 text-base">
              <span className="font-semibold">{lang === "en" ? "City:" : "Ciudad:"}</span>{" "}
              {clinic.city}, {clinic.state}
            </p>
            <p className="text-base">
              <span className="font-semibold">{lang === "en" ? "Phone:" : "Teléfono:"}</span>{" "}
              {clinic.phone}
            </p>
            <p className="text-base">
              <span className="font-semibold">{lang === "en" ? "Hours:" : "Horario:"}</span>{" "}
              {clinic.hours}
            </p>
          </article>
        ))}
      </div>
      <div className="hidden overflow-x-auto md:block">
        <table className="min-w-full rounded-lg border border-gray-100 bg-white text-lg shadow">
          <thead className="bg-blue-100 text-blue-800">
            <tr>
              <th className="px-2 py-3 text-left">
                {lang === "en" ? "Clinic name" : "Nombre de la clínica"}
              </th>
              <th className="px-2 py-3 text-left">{lang === "en" ? "City" : "Ciudad"}</th>
              <th className="px-2 py-3 text-left">{lang === "en" ? "State" : "Estado"}</th>
              <th className="px-2 py-3 text-left">{lang === "en" ? "Phone" : "Teléfono"}</th>
              <th className="px-2 py-3 text-left">{lang === "en" ? "Hours" : "Horario"}</th>
            </tr>
          </thead>
          <tbody className="[&>tr:nth-child(even)]:bg-slate-50">
            {clinics.map((clinic) => (
              <tr key={clinic.name}>
                <td className="px-2 py-2">{clinic.name}</td>
                <td className="px-2 py-2">{clinic.city}</td>
                <td className="px-2 py-2">{clinic.state}</td>
                <td className="px-2 py-2">{clinic.phone}</td>
                <td className="px-2 py-2">{clinic.hours}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}
