import { Appointment, AppointmentStatus, Claim } from "../types/models";

type ClaimFilter = Partial<Pick<Claim, "locationId" | "status" | "payerName" | "serviceType">>;

type GroupableClaimKey = "locationId" | "payerName" | "status" | "serviceType";

const claimFilterEntries = (filters: ClaimFilter): [keyof ClaimFilter, string][] => {
  return Object.entries(filters) as [keyof ClaimFilter, string][];
};

const claimFieldMatches = (claim: Claim, field: keyof ClaimFilter, value: string): boolean => {
  return claim[field] === value;
};

const compareByDirection = (first: string, second: string, direction: "asc" | "desc"): number => {
  const result = first.localeCompare(second);
  return direction === "asc" ? result : -result;
};

const claimIdComparator = (direction: "asc" | "desc") => {
  return (first: Claim, second: Claim): number => compareByDirection(first.claimId, second.claimId, direction);
};

const appointmentDateComparator = (direction: "asc" | "desc") => {
  return (first: Appointment, second: Appointment): number =>
    compareByDirection(first.scheduledDate, second.scheduledDate, direction);
};

const groupedBucket = (grouped: Record<string, Claim[]>, key: string): Claim[] => {
  if (!grouped[key]) {
    grouped[key] = [];
  }
  return grouped[key];
};

export const filterClaims = (claims: Claim[], filters: ClaimFilter): Claim[] => {
  const entries = claimFilterEntries(filters);
  return claims.filter((claim) => entries.every(([field, value]) => claimFieldMatches(claim, field, value)));
};

export const filterAppointmentsByStatus = (
  appointments: Appointment[],
  status: AppointmentStatus[]
): Appointment[] => {
  return appointments.filter((appointment) => status.includes(appointment.status));
};

export const sortClaimsById = (claims: Claim[], direction: "asc" | "desc"): Claim[] => {
  return [...claims].sort(claimIdComparator(direction));
};

export const sortAppointmentsByDate = (
  appointments: Appointment[],
  direction: "asc" | "desc"
): Appointment[] => {
  return [...appointments].sort(appointmentDateComparator(direction));
};

export const groupClaimsBy = (claims: Claim[], key: GroupableClaimKey): Record<string, Claim[]> => {
  return claims.reduce<Record<string, Claim[]>>((grouped, claim) => {
    const groupKey = claim[key];
    groupedBucket(grouped, groupKey).push(claim);
    return grouped;
  }, {});
};
