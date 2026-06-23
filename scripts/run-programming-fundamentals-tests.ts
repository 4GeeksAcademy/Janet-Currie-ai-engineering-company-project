import {
  knownLocationIds,
  sampleAppointments,
  sampleClaims,
  sampleClinicians,
  sampleLocations,
} from "../src/types/sampleData";
import {
  filterAppointmentsByStatus,
  filterClaims,
  groupClaimsBy,
  sortAppointmentsByDate,
  sortClaimsById,
} from "../src/utils/collections";
import { binarySearchClaimById, findClaimById, findClinicianById } from "../src/utils/search";
import {
  calculateDenialRate,
  calculateNoShowCost,
  denialRateByLocation,
  denialRateByPayer,
  flagHighDenialPayers,
  flagHighNoShowLocations,
  generateCMEReport,
  getCliniciansAtRisk,
  getCliniciansWithExpiringLicences,
  noShowRateByLocation,
} from "../src/utils/transformations";
import {
  isDenialRateAboveThreshold,
  isNoShowRateAboveThreshold,
  validateClaim,
  validateClinician,
} from "../src/utils/validations";

const asOfDate = "2026-06-20";

const sortedClaimsAsc = sortClaimsById(sampleClaims, "asc");
const denialRate = calculateDenialRate(sampleClaims);
const noShowRates = noShowRateByLocation(sampleAppointments);

console.log("=== Collections ===");
console.log("filterClaims", filterClaims(sampleClaims, { payerName: "BlueCross", status: "denied" }));
console.log("filterAppointmentsByStatus", filterAppointmentsByStatus(sampleAppointments, ["no_show"]));
console.log("sortClaimsById", sortedClaimsAsc.map((c) => c.claimId));
console.log("sortAppointmentsByDate", sortAppointmentsByDate(sampleAppointments, "asc").map((a) => a.appointmentId));
console.log("groupClaimsBy", Object.keys(groupClaimsBy(sampleClaims, "payerName")));

console.log("\n=== Search ===");
console.log("findClaimById", findClaimById(sampleClaims, "CLM-000004"));
console.log("findClinicianById", findClinicianById(sampleClinicians, "CLN-000002"));
console.log("binarySearchClaimById", binarySearchClaimById(sortedClaimsAsc, "CLM-000003"));

console.log("\n=== Transformations ===");
console.log("calculateDenialRate", denialRate);
console.log("denialRateByPayer", denialRateByPayer(sampleClaims));
console.log("denialRateByLocation", denialRateByLocation(sampleClaims));
console.log("flagHighDenialPayers", flagHighDenialPayers(sampleClaims));
console.log("calculateNoShowCost", calculateNoShowCost(sampleAppointments, sampleLocations[1], "2025-03-14"));
console.log("noShowRateByLocation", noShowRates);
console.log("flagHighNoShowLocations", flagHighNoShowLocations(sampleAppointments));

console.log("\n=== CME ===");
console.log("generateCMEReport", generateCMEReport(sampleClinicians, asOfDate));
console.log("getCliniciansAtRisk", getCliniciansAtRisk(sampleClinicians, asOfDate));
console.log(
  "getCliniciansWithExpiringLicences(90)",
  getCliniciansWithExpiringLicences(sampleClinicians, asOfDate, 90)
);
console.log(
  "getCliniciansWithExpiringLicences(30)",
  getCliniciansWithExpiringLicences(sampleClinicians, asOfDate, 30)
);

console.log("\n=== Validations ===");
console.log("validateClaim", validateClaim(sampleClaims[1], knownLocationIds));
console.log("validateClinician(valid)", validateClinician(sampleClinicians[0]));
const invalidRoleClinician = { ...sampleClinicians[0], role: "invalid_role" } as any;
console.log("validateClinician(invalid role)", validateClinician(invalidRoleClinician));
console.log("isDenialRateAboveThreshold", isDenialRateAboveThreshold(denialRate));
console.log(
  "isNoShowRateAboveThreshold(us-fl-001)",
  isNoShowRateAboveThreshold(noShowRates["us-fl-001"] ?? 0)
);
