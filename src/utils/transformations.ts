import {
  Appointment,
  Claim,
  Clinician,
  CMEReport,
  CMEStatus,
  Location,
} from "../types/models";

const MS_PER_DAY = 24 * 60 * 60 * 1000;

const parseDate = (dateValue: string): Date => {
  return new Date(`${dateValue}T00:00:00Z`);
};

const roundToTwo = (value: number): number => {
  return Number(value.toFixed(2));
};

const roundToOne = (value: number): number => {
  return Number(value.toFixed(1));
};

const percentage = (part: number, whole: number): number => {
  if (whole === 0) {
    return 0;
  }
  return (part / whole) * 100;
};

const calendarDayDiff = (fromDate: string, toDate: string): number => {
  const from = parseDate(fromDate);
  const to = parseDate(toDate);
  return Math.ceil((to.getTime() - from.getTime()) / MS_PER_DAY);
};

const groupCount = <T>(items: T[], keyFn: (item: T) => string): Record<string, T[]> => {
  return items.reduce<Record<string, T[]>>((acc, item) => {
    const key = keyFn(item);
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(item);
    return acc;
  }, {});
};

const deniedClaims = (claims: Claim[]): Claim[] => {
  return claims.filter((claim) => claim.status === "denied");
};

const rateFromClaims = (claims: Claim[]): number => {
  return roundToTwo(percentage(deniedClaims(claims).length, claims.length));
};

const dateInInclusiveRange = (dateValue: string, start: string, end: string): boolean => {
  const date = parseDate(dateValue).getTime();
  const rangeStart = parseDate(start).getTime();
  const rangeEnd = parseDate(end).getTime();
  return date >= rangeStart && date <= rangeEnd;
};

const weekStartDate = (weekEndingDate: string): string => {
  const end = parseDate(weekEndingDate);
  const start = new Date(end.getTime() - 6 * MS_PER_DAY);
  return start.toISOString().slice(0, 10);
};

const isNoShow = (appointment: Appointment): boolean => {
  return appointment.status === "no_show";
};

const noShowAppointments = (appointments: Appointment[]): Appointment[] => {
  return appointments.filter(isNoShow);
};

const appointmentInWeekWindow = (appointment: Appointment, start: string, end: string): boolean => {
  return dateInInclusiveRange(appointment.scheduledDate, start, end);
};

const cycleEndDate = (cycleStartDate: string): string => {
  const start = parseDate(cycleStartDate);
  const end = new Date(Date.UTC(start.getUTCFullYear() + 1, start.getUTCMonth(), start.getUTCDate() - 1));
  return end.toISOString().slice(0, 10);
};

const totalCycleDays = (cycleStartDate: string): number => {
  const cycleEnd = cycleEndDate(cycleStartDate);
  return calendarDayDiff(cycleStartDate, cycleEnd) + 1;
};

const elapsedCycleDays = (cycleStartDate: string, asOfDate: string): number => {
  const elapsed = calendarDayDiff(cycleStartDate, asOfDate) + 1;
  if (elapsed < 0) {
    return 0;
  }
  return elapsed;
};

const elapsedCyclePercent = (cycleStartDate: string, asOfDate: string): number => {
  const elapsed = elapsedCycleDays(cycleStartDate, asOfDate);
  const total = totalCycleDays(cycleStartDate);
  const raw = percentage(elapsed, total);
  if (raw < 0) {
    return 0;
  }
  if (raw > 100) {
    return 100;
  }
  return raw;
};

const clinicianPercentComplete = (required: number, logged: number): number => {
  if (required === 0) {
    return 100;
  }
  return roundToOne(percentage(logged, required));
};

const statusForClinician = (
  hoursRequired: number,
  hoursLogged: number,
  cycleStartDate: string,
  asOfDate: string
): CMEStatus => {
  if (hoursLogged >= hoursRequired) {
    return "complete";
  }

  const cycleEnd = cycleEndDate(cycleStartDate);
  const daysRemaining = calendarDayDiff(asOfDate, cycleEnd);

  if (daysRemaining < 0) {
    return "overdue";
  }

  const completion = clinicianPercentComplete(hoursRequired, hoursLogged);
  const expectedProgress = elapsedCyclePercent(cycleStartDate, asOfDate);

  if (completion < expectedProgress - 15) {
    return "at_risk";
  }

  return "on_track";
};

export const calculateDenialRate = (claims: Claim[]): number => {
  if (claims.length === 0) {
    throw new Error("Claims array cannot be empty.");
  }

  return rateFromClaims(claims);
};

export const denialRateByPayer = (claims: Claim[]): Record<string, number> => {
  const grouped = groupCount(claims, (claim) => claim.payerName);
  return Object.fromEntries(
    Object.entries(grouped).map(([payerName, payerClaims]) => [payerName, rateFromClaims(payerClaims)])
  );
};

export const denialRateByLocation = (claims: Claim[]): Record<string, number> => {
  const grouped = groupCount(claims, (claim) => claim.locationId);
  return Object.fromEntries(
    Object.entries(grouped).map(([locationId, locationClaims]) => [locationId, rateFromClaims(locationClaims)])
  );
};

export const flagHighDenialPayers = (claims: Claim[], threshold = 8): string[] => {
  const rates = denialRateByPayer(claims);
  return Object.entries(rates)
    .filter(([, rate]) => rate > threshold)
    .map(([payerName]) => payerName);
};

export const calculateNoShowCost = (
  appointments: Appointment[],
  location: Location,
  weekEndingDate: string
): number => {
  const rangeStart = weekStartDate(weekEndingDate);
  const rangeEnd = weekEndingDate;

  const total = appointments
    .filter((appointment) => appointment.locationId === location.locationId)
    .filter(isNoShow)
    .filter((appointment) => appointmentInWeekWindow(appointment, rangeStart, rangeEnd))
    .reduce((sum, appointment) => sum + location.averageConsultationFee[appointment.serviceType], 0);

  return roundToTwo(total);
};

export const noShowRateByLocation = (appointments: Appointment[]): Record<string, number> => {
  const grouped = groupCount(appointments, (appointment) => appointment.locationId);

  return Object.fromEntries(
    Object.entries(grouped).map(([locationId, locationAppointments]) => {
      const rate = percentage(noShowAppointments(locationAppointments).length, locationAppointments.length);
      return [locationId, roundToTwo(rate)];
    })
  );
};

export const flagHighNoShowLocations = (appointments: Appointment[], threshold = 20): string[] => {
  const rates = noShowRateByLocation(appointments);
  return Object.entries(rates)
    .filter(([, rate]) => rate > threshold)
    .map(([locationId]) => locationId);
};

export const generateCMEReport = (clinicians: Clinician[], asOfDate: string): CMEReport[] => {
  return clinicians.map((clinician) => {
    const cycleEnd = cycleEndDate(clinician.cmeYearStartDate);
    const hoursRemaining = Math.max(0, clinician.cmeHoursRequired - clinician.cmeHoursLogged);

    return {
      clinicianId: clinician.clinicianId,
      fullName: `${clinician.firstName} ${clinician.lastName}`,
      role: clinician.role,
      locationId: clinician.locationId,
      hoursRequired: clinician.cmeHoursRequired,
      hoursLogged: clinician.cmeHoursLogged,
      hoursRemaining,
      percentComplete: clinicianPercentComplete(clinician.cmeHoursRequired, clinician.cmeHoursLogged),
      daysRemainingInCycle: calendarDayDiff(asOfDate, cycleEnd),
      complianceStatus: statusForClinician(
        clinician.cmeHoursRequired,
        clinician.cmeHoursLogged,
        clinician.cmeYearStartDate,
        asOfDate
      ),
      licenceExpiryDate: clinician.licenceExpiryDate,
      licenceDaysRemaining: calendarDayDiff(asOfDate, clinician.licenceExpiryDate),
    };
  });
};

export const getCliniciansAtRisk = (clinicians: Clinician[], asOfDate: string): Clinician[] => {
  const atRiskIds = new Set(
    generateCMEReport(clinicians, asOfDate)
      .filter((entry) => entry.complianceStatus === "at_risk" || entry.complianceStatus === "overdue")
      .map((entry) => entry.clinicianId)
  );

  return clinicians.filter((clinician) => atRiskIds.has(clinician.clinicianId));
};

export const getCliniciansWithExpiringLicences = (
  clinicians: Clinician[],
  asOfDate: string,
  daysThreshold: number
): Clinician[] => {
  return clinicians.filter((clinician) => {
    const daysRemaining = calendarDayDiff(asOfDate, clinician.licenceExpiryDate);
    return daysRemaining >= 0 && daysRemaining <= daysThreshold;
  });
};
