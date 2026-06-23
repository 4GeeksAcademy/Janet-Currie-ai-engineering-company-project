import { Claim, Clinician } from "../types/models";

interface ValidationResult {
  valid: boolean;
  errors: string[];
}

const isValidDate = (dateValue: string): boolean => {
  const parsed = new Date(dateValue);
  return !Number.isNaN(parsed.getTime());
};

const todayIsoDate = (): string => {
  return new Date().toISOString().slice(0, 10);
};

const isFutureDate = (dateValue: string): boolean => {
  return dateValue > todayIsoDate();
};

const isPatientIdFormatValid = (patientId: string): boolean => {
  return /^HC-[A-Za-z0-9]{6}$/.test(patientId);
};

const hasValidClaimAmount = (amount: number): boolean => {
  return amount > 0;
};

const isKnownLocation = (locationId: string, knownLocationIds: string[]): boolean => {
  return knownLocationIds.includes(locationId);
};

const hasDenialReasonWhenDenied = (claim: Claim): boolean => {
  if (claim.status !== "denied") {
    return true;
  }
  return Boolean(claim.denialReason);
};

const nonNegative = (value: number): boolean => {
  return value >= 0;
};

const validClinicianRoles = ["physician", "nurse_practitioner", "nurse", "medical_assistant"] as const;

const hasValidClinicianRole = (role: string): boolean => {
  return validClinicianRoles.includes(role as (typeof validClinicianRoles)[number]);
};

const dateIsTodayOrLater = (dateValue: string): boolean => {
  return dateValue >= todayIsoDate();
};

const addError = (errors: string[], condition: boolean, message: string): void => {
  if (!condition) {
    errors.push(message);
  }
};

export const validateClaim = (claim: Claim, knownLocationIds: string[]): ValidationResult => {
  const errors: string[] = [];

  addError(errors, hasValidClaimAmount(claim.claimAmount), "claimAmount must be greater than 0.");
  addError(errors, isValidDate(claim.submissionDate), "submissionDate must be a valid date.");
  addError(
    errors,
    !isFutureDate(claim.submissionDate),
    "submissionDate must not be a future date."
  );
  addError(
    errors,
    isKnownLocation(claim.locationId, knownLocationIds),
    "locationId must match a known clinic ID."
  );
  addError(
    errors,
    hasDenialReasonWhenDenied(claim),
    "denialReason is required when claim status is denied."
  );
  addError(
    errors,
    isPatientIdFormatValid(claim.patientId),
    "patientId must match format HC- followed by 6 alphanumeric characters."
  );

  return {
    valid: errors.length === 0,
    errors,
  };
};

export const validateClinician = (clinician: Clinician): ValidationResult => {
  const errors: string[] = [];

  addError(
    errors,
    nonNegative(clinician.cmeHoursRequired),
    "cmeHoursRequired must be greater than or equal to 0."
  );
  addError(
    errors,
    nonNegative(clinician.cmeHoursLogged),
    "cmeHoursLogged must be greater than or equal to 0."
  );
  addError(
    errors,
    isValidDate(clinician.licenceExpiryDate),
    "licenceExpiryDate must be a valid date."
  );
  addError(
    errors,
    dateIsTodayOrLater(clinician.licenceExpiryDate),
    "licenceExpiryDate must be today or a future date."
  );
  addError(
    errors,
    hasValidClinicianRole(clinician.role),
    "role must be one of: physician, nurse_practitioner, nurse, medical_assistant."
  );

  return {
    valid: errors.length === 0,
    errors,
  };
};

export const isDenialRateAboveThreshold = (rate: number, threshold = 8): boolean => {
  return rate > threshold;
};

export const isNoShowRateAboveThreshold = (rate: number, threshold = 20): boolean => {
  return rate > threshold;
};
