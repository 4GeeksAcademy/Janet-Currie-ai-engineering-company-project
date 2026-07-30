export type Clinic = {
  name: string;
  city: string;
  state: string;
  phone: string;
  hours: string;
  eveningCloseHour: number;
};

export const clinics: Clinic[] = [
  {
    name: "HealthCore Austin Central",
    city: "Austin",
    state: "TX",
    phone: "(512) 340-8800",
    hours: "Mon–Fri 7am–8pm · Sat 9am–3pm",
    eveningCloseHour: 20,
  },
  {
    name: "HealthCore Austin North",
    city: "Austin",
    state: "TX",
    phone: "(512) 340-8810",
    hours: "Mon–Fri 8am–7pm",
    eveningCloseHour: 19,
  },
  {
    name: "HealthCore San Antonio",
    city: "San Antonio",
    state: "TX",
    phone: "(210) 720-4400",
    hours: "Mon–Fri 8am–6pm · Sat 9am–1pm",
    eveningCloseHour: 18,
  },
  {
    name: "HealthCore Miami",
    city: "Miami",
    state: "FL",
    phone: "(305) 510-7700",
    hours: "Mon–Fri 7am–8pm · Sat 9am–4pm",
    eveningCloseHour: 20,
  },
  {
    name: "HealthCore Orlando",
    city: "Orlando",
    state: "FL",
    phone: "(407) 892-6600",
    hours: "Mon–Fri 8am–6pm",
    eveningCloseHour: 18,
  },
  {
    name: "HealthCore Atlanta",
    city: "Atlanta",
    state: "GA",
    phone: "(404) 330-9900",
    hours: "Mon–Fri 8am–7pm",
    eveningCloseHour: 19,
  },
];
