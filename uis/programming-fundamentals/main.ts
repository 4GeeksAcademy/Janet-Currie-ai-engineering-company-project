import {
  knownLocationIds,
  sampleAppointments,
  sampleClaims,
  sampleClinicians,
  sampleLocations,
} from "../../src/types/sampleData";
import {
  filterAppointmentsByStatus,
  filterClaims,
  groupClaimsBy,
  sortAppointmentsByDate,
  sortClaimsById,
} from "../../src/utils/collections";
import {
  binarySearchClaimById,
  findClaimById,
  findClinicianById,
} from "../../src/utils/search";
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
} from "../../src/utils/transformations";
import {
  isDenialRateAboveThreshold,
  isNoShowRateAboveThreshold,
  validateClaim,
  validateClinician,
} from "../../src/utils/validations";

const getElement = (id: string): HTMLElement => {
  const element = document.getElementById(id);
  if (!element) {
    throw new Error(`Element with id '${id}' was not found.`);
  }
  return element;
};

const writeJson = (id: string, data: unknown): void => {
  getElement(id).textContent = JSON.stringify(data, null, 2);
};

const bindClick = (id: string, onClick: () => void): void => {
  getElement(id).addEventListener("click", onClick);
};

const renderCollectionsSection = (): void => {
  bindClick("btn-filter-claims", () => {
    writeJson(
      "out-collections",
      filterClaims(sampleClaims, { payerName: "BlueCross", status: "denied" })
    );
  });

  bindClick("btn-sort-claims", () => {
    const sorted = sortClaimsById(sampleClaims, "desc");
    writeJson("out-collections", { sorted, originalUnchanged: sampleClaims });
  });

  bindClick("btn-sort-appointments", () => {
    writeJson("out-collections", sortAppointmentsByDate(sampleAppointments, "asc"));
  });

  bindClick("btn-group-claims", () => {
    writeJson("out-collections", groupClaimsBy(sampleClaims, "payerName"));
  });
};

const renderSearchSection = (): void => {
  bindClick("btn-find-claim", () => {
    writeJson("out-search", findClaimById(sampleClaims, "CLM-000004"));
  });

  bindClick("btn-find-clinician", () => {
    writeJson("out-search", findClinicianById(sampleClinicians, "CLN-000002"));
  });

  bindClick("btn-binary-search", () => {
    const sortedClaims = sortClaimsById(sampleClaims, "asc");
    const index = binarySearchClaimById(sortedClaims, "CLM-000003");
    writeJson("out-search", { sortedClaims, index });
  });
};

const renderTransformationSection = (): void => {
  bindClick("btn-denial-rates", () => {
    const denialRate = calculateDenialRate(sampleClaims);
    writeJson("out-transformations", {
      denialRate,
      denialRateByPayer: denialRateByPayer(sampleClaims),
      denialRateByLocation: denialRateByLocation(sampleClaims),
      highDenialPayersAbove8: flagHighDenialPayers(sampleClaims),
      denialRateAboveDefaultThreshold: isDenialRateAboveThreshold(denialRate),
    });
  });

  bindClick("btn-no-show", () => {
    const noShowRates = noShowRateByLocation(sampleAppointments);
    writeJson("out-transformations", {
      noShowRateByLocation: noShowRates,
      filteredNoShows: filterAppointmentsByStatus(sampleAppointments, ["no_show"]),
      noShowCostMiami: calculateNoShowCost(sampleAppointments, sampleLocations[1], "2025-03-14"),
      highNoShowLocationsAbove20: flagHighNoShowLocations(sampleAppointments),
      miamiNoShowRateAboveDefaultThreshold: isNoShowRateAboveThreshold(noShowRates["us-fl-001"] ?? 0),
    });
  });
};

const renderValidationSection = (): void => {
  bindClick("btn-cme", () => {
    const asOfDate = "2026-06-20";
    writeJson("out-validation", {
      cmeReport: generateCMEReport(sampleClinicians, asOfDate),
      cliniciansAtRisk: getCliniciansAtRisk(sampleClinicians, asOfDate),
      cliniciansWithLicencesExpiringIn90Days: getCliniciansWithExpiringLicences(
        sampleClinicians,
        asOfDate,
        90
      ),
      cliniciansWithLicencesExpiringIn30Days: getCliniciansWithExpiringLicences(
        sampleClinicians,
        asOfDate,
        30
      ),
    });
  });

  bindClick("btn-validations", () => {
    const invalidRoleClinician = {
      ...sampleClinicians[0],
      role: "invalid_role",
    } as unknown as (typeof sampleClinicians)[number];

    writeJson("out-validation", {
      claimValidation: validateClaim(sampleClaims[1], knownLocationIds),
      clinicianValidation: validateClinician(sampleClinicians[0]),
      invalidClinicianRoleValidation: validateClinician(invalidRoleClinician),
    });
  });
};

const renderReadyState = (): void => {
  writeJson("out-collections", { status: "Ready", section: "Collections" });
  writeJson("out-search", { status: "Ready", section: "Search" });
  writeJson("out-transformations", { status: "Ready", section: "Transformations" });
  writeJson("out-validation", { status: "Ready", section: "CME and Validation" });
};

const bootstrap = (): void => {
  renderCollectionsSection();
  renderSearchSection();
  renderTransformationSection();
  renderValidationSection();
  renderReadyState();
};

bootstrap();
