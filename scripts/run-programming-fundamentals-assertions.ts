import assert from "node:assert/strict";

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

type TestCase = {
  name: string;
  run: () => void;
};

const asOfDate = "2026-06-20";

const tests: TestCase[] = [
  {
    name: "filterClaims returns denied BlueCross claim",
    run: () => {
      const result = filterClaims(sampleClaims, { payerName: "BlueCross", status: "denied" });
      assert.equal(result.length, 1);
      assert.equal(result[0].claimId, "CLM-000004");
    },
  },
  {
    name: "filterAppointmentsByStatus returns all no-shows",
    run: () => {
      const result = filterAppointmentsByStatus(sampleAppointments, ["no_show"]);
      assert.equal(result.length, 3);
    },
  },
  {
    name: "sortClaimsById asc preserves expected order",
    run: () => {
      const ids = sortClaimsById(sampleClaims, "asc").map((claim) => claim.claimId);
      assert.deepEqual(ids, ["CLM-000001", "CLM-000002", "CLM-000003", "CLM-000004", "CLM-000005"]);
    },
  },
  {
    name: "sortAppointmentsByDate asc preserves expected order",
    run: () => {
      const ids = sortAppointmentsByDate(sampleAppointments, "asc").map((appointment) => appointment.appointmentId);
      assert.deepEqual(ids, ["APT-000001", "APT-000002", "APT-000003", "APT-000004", "APT-000005"]);
    },
  },
  {
    name: "groupClaimsBy payerName has expected buckets",
    run: () => {
      const grouped = groupClaimsBy(sampleClaims, "payerName");
      assert.deepEqual(Object.keys(grouped), ["BlueCross", "Aetna", "Medicare", "Cigna"]);
      assert.equal(grouped.BlueCross.length, 2);
    },
  },
  {
    name: "findClaimById finds CLM-000004",
    run: () => {
      const claim = findClaimById(sampleClaims, "CLM-000004");
      assert.ok(claim);
      assert.equal(claim.claimId, "CLM-000004");
    },
  },
  {
    name: "findClinicianById finds CLN-000002",
    run: () => {
      const clinician = findClinicianById(sampleClinicians, "CLN-000002");
      assert.ok(clinician);
      assert.equal(clinician.clinicianId, "CLN-000002");
    },
  },
  {
    name: "binarySearchClaimById returns correct index",
    run: () => {
      const sortedClaims = sortClaimsById(sampleClaims, "asc");
      assert.equal(binarySearchClaimById(sortedClaims, "CLM-000003"), 2);
    },
  },
  {
    name: "calculateDenialRate matches expected value",
    run: () => {
      assert.equal(calculateDenialRate(sampleClaims), 40);
    },
  },
  {
    name: "denialRateByPayer matches expected values",
    run: () => {
      assert.deepEqual(denialRateByPayer(sampleClaims), {
        BlueCross: 50,
        Aetna: 100,
        Medicare: 0,
        Cigna: 0,
      });
    },
  },
  {
    name: "denialRateByLocation matches expected values",
    run: () => {
      assert.deepEqual(denialRateByLocation(sampleClaims), {
        "us-tx-001": 50,
        "us-fl-001": 50,
        "us-ga-001": 0,
      });
    },
  },
  {
    name: "flagHighDenialPayers returns expected payers",
    run: () => {
      assert.deepEqual(flagHighDenialPayers(sampleClaims), ["BlueCross", "Aetna"]);
    },
  },
  {
    name: "calculateNoShowCost for Miami matches expected value",
    run: () => {
      assert.equal(calculateNoShowCost(sampleAppointments, sampleLocations[1], "2025-03-14"), 555);
    },
  },
  {
    name: "noShowRateByLocation matches expected values",
    run: () => {
      assert.deepEqual(noShowRateByLocation(sampleAppointments), {
        "us-tx-001": 50,
        "us-fl-001": 100,
        "us-ga-001": 0,
      });
    },
  },
  {
    name: "flagHighNoShowLocations returns expected locations",
    run: () => {
      assert.deepEqual(flagHighNoShowLocations(sampleAppointments), ["us-tx-001", "us-fl-001"]);
    },
  },
  {
    name: "generateCMEReport returns expected status sequence",
    run: () => {
      const report = generateCMEReport(sampleClinicians, asOfDate);
      assert.equal(report.length, 3);
      assert.deepEqual(report.map((entry) => entry.complianceStatus), ["overdue", "overdue", "complete"]);
    },
  },
  {
    name: "getCliniciansAtRisk returns expected clinician IDs",
    run: () => {
      const atRiskIds = getCliniciansAtRisk(sampleClinicians, asOfDate).map((clinician) => clinician.clinicianId);
      assert.deepEqual(atRiskIds, ["CLN-000001", "CLN-000002"]);
    },
  },
  {
    name: "getCliniciansWithExpiringLicences works for 90 and 30 days",
    run: () => {
      const in90 = getCliniciansWithExpiringLicences(sampleClinicians, asOfDate, 90).map(
        (clinician) => clinician.clinicianId
      );
      const in30 = getCliniciansWithExpiringLicences(sampleClinicians, asOfDate, 30).map(
        (clinician) => clinician.clinicianId
      );
      assert.deepEqual(in90, ["CLN-000001"]);
      assert.deepEqual(in30, ["CLN-000001"]);
    },
  },
  {
    name: "validateClaim passes valid sample claim",
    run: () => {
      assert.deepEqual(validateClaim(sampleClaims[1], knownLocationIds), { valid: true, errors: [] });
    },
  },
  {
    name: "validateClinician catches invalid role",
    run: () => {
      const valid = validateClinician(sampleClinicians[0]);
      const invalid = validateClinician({ ...sampleClinicians[0], role: "invalid_role" as never });
      assert.deepEqual(valid, { valid: true, errors: [] });
      assert.equal(invalid.valid, false);
      assert.ok(
        invalid.errors.includes("role must be one of: physician, nurse_practitioner, nurse, medical_assistant.")
      );
    },
  },
  {
    name: "threshold helpers return expected booleans",
    run: () => {
      const denialRate = calculateDenialRate(sampleClaims);
      const noShowRate = noShowRateByLocation(sampleAppointments)["us-fl-001"];
      assert.equal(isDenialRateAboveThreshold(denialRate), true);
      assert.equal(isNoShowRateAboveThreshold(noShowRate), true);
    },
  },
];

let passed = 0;

for (const test of tests) {
  try {
    test.run();
    passed += 1;
    console.log(`PASS - ${test.name}`);
  } catch (error) {
    console.error(`FAIL - ${test.name}`);
    console.error(error);
    process.exitCode = 1;
  }
}

console.log(`\n${passed}/${tests.length} tests passed.`);
