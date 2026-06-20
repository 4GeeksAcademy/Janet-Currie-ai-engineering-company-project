import { Claim, Clinician } from "../types/models";

const middleIndex = (left: number, right: number): number => {
  return Math.floor((left + right) / 2);
};

export const findClaimById = (claims: Claim[], claimId: string): Claim | null => {
  const match = claims.find((claim) => claim.claimId === claimId);
  return match ?? null;
};

export const findClinicianById = (clinicians: Clinician[], clinicianId: string): Clinician | null => {
  const match = clinicians.find((clinician) => clinician.clinicianId === clinicianId);
  return match ?? null;
};

export const binarySearchClaimById = (sortedClaims: Claim[], targetId: string): number => {
  let left = 0;
  let right = sortedClaims.length - 1;

  while (left <= right) {
    const mid = middleIndex(left, right);
    const currentId = sortedClaims[mid].claimId;

    if (currentId === targetId) {
      return mid;
    }

    if (currentId < targetId) {
      left = mid + 1;
      continue;
    }

    right = mid - 1;
  }

  return -1;
};
