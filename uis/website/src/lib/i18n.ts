export type Lang = "en" | "es";

export type LocalizedString = {
  en: string;
  es: string;
};

export function t(value: LocalizedString, lang: Lang): string {
  return value[lang];
}

export const navItems: { href: string; label: LocalizedString }[] = [
  { href: "#home", label: { en: "Home", es: "Inicio" } },
  { href: "#why-healthcore", label: { en: "Why HealthCore", es: "¿Por qué HealthCore?" } },
  { href: "#services", label: { en: "Services", es: "Servicios" } },
  { href: "#locations", label: { en: "Locations", es: "Ubicaciones" } },
  { href: "#contact", label: { en: "Contact", es: "Contacto" } },
];

export const heroCopy = {
  headline: {
    en: "Healthcare that fits your life",
    es: "Atención médica que se adapta a tu vida",
  },
  taglines: [
    {
      en: "12 outpatient clinics across the US and UK",
      es: "12 clínicas ambulatorias en EE. UU. y el Reino Unido",
    },
    {
      en: "Same-day appointments and extended hours",
      es: "Citas el mismo día y horario extendido",
    },
    {
      en: "Bilingual care",
      es: "Atención bilingüe",
    },
    {
      en: "The attention you need when you need it",
      es: "La atención que necesita cuando la necesita",
    },
  ],
  cta: {
    en: "Request an appointment",
    es: "Solicitar una cita",
  },
};

export const whyHealthCore = {
  title: { en: "Why HealthCore", es: "¿Por qué HealthCore?" },
  cards: [
    {
      title: { en: "Access & Availability", es: "Acceso y Disponibilidad" },
      items: [
        {
          en: "Same-day appointments at most locations",
          es: "Citas el mismo día en la mayoría de las ubicaciones",
        },
        {
          en: "Extended hours — weekdays until 7pm or 8pm, Saturdays available",
          es: "Horario extendido: entre semana hasta las 7 u 8 pm, sábados disponibles",
        },
      ],
    },
    {
      title: { en: "Communication & Reach", es: "Comunicación y Cobertura" },
      items: [
        {
          en: "Bilingual staff in English and Spanish at US locations",
          es: "Personal bilingüe en inglés y español en ubicaciones de EE. UU.",
        },
        {
          en: "12 clinics across Texas, Florida, Georgia, and the United Kingdom",
          es: "12 clínicas en Texas, Florida, Georgia y el Reino Unido",
        },
      ],
    },
  ],
};

export const services = {
  title: { en: "Our Services", es: "Nuestros Servicios" },
  items: [
    {
      title: {
        en: "Primary Care & Chronic Disease",
        es: "Atención primaria y enfermedades crónicas",
      },
      bullets: [
        {
          en: "Same-day appointments with primary care physicians",
          es: "Citas el mismo día con médicos de atención primaria",
        },
        {
          en: "Ongoing management of diabetes, hypertension, and asthma",
          es: "Manejo continuo de diabetes, hipertensión y asma",
        },
      ],
    },
    {
      title: { en: "Specialist Consultations", es: "Consultas con especialistas" },
      bullets: [
        {
          en: "Cardiology, endocrinology, pulmonology, and women's health",
          es: "Cardiología, endocrinología, neumología y salud de la mujer",
        },
        {
          en: "Referrals coordinated within the HealthCore network",
          es: "Referencias coordinadas dentro de la red HealthCore",
        },
      ],
    },
    {
      title: {
        en: "Preventive Health & Wellbeing",
        es: "Salud preventiva y bienestar",
      },
      bullets: [
        {
          en: "Screenings, vaccinations, and annual check-ups",
          es: "Exámenes, vacunas y chequeos anuales",
        },
        {
          en: "Mental health counselling and psychiatry referrals",
          es: "Consejería de salud mental y referencias a psiquiatría",
        },
      ],
    },
  ],
};

export const contactCopy = {
  title: { en: "Contact", es: "Contacto" },
  lines: [
    {
      label: { en: "General enquiries:", es: "Consultas generales:" },
      value: "info@healthcore.com",
      href: "mailto:info@healthcore.com",
    },
    {
      label: { en: "Austin HQ:", es: "Sede Austin:" },
      value: "(512) 340-8800",
      href: "tel:+15123408800",
    },
    {
      label: { en: "Miami:", es: "Miami:" },
      value: "(305) 510-7700",
      href: "tel:+13055107700",
    },
    {
      label: { en: "UK (London):", es: "Reino Unido (Londres):" },
      value: "+44 20 7946 0100",
      href: "tel:+442079460100",
    },
  ],
  emergency: {
    en: "If this is a medical emergency, call 9-1-1",
    es: "Si es una emergencia médica, llame al 9-1-1",
  },
  quickHelp: {
    en: "Need help now? Call our Austin front desk.",
    es: "¿Necesita ayuda ahora? Llame a nuestra recepción en Austin.",
  },
  callNow: { en: "Call now", es: "Llamar ahora" },
};
