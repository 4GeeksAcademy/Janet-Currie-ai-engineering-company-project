// ../../src/types/sampleData.ts
var sampleLocations = [
  {
    locationId: "us-tx-001",
    name: "HealthCore Austin Central",
    city: "Austin",
    stateOrCountry: "TX",
    country: "US",
    phone: "(512) 340-8800",
    averageConsultationFee: {
      primary_care: 180,
      chronic_disease: 220,
      preventive: 150,
      specialist: 320,
      womens_health: 240,
      paediatric: 175,
      mental_health: 200
    }
  },
  {
    locationId: "us-fl-001",
    name: "HealthCore Miami",
    city: "Miami",
    stateOrCountry: "FL",
    country: "US",
    phone: "(305) 510-7700",
    averageConsultationFee: {
      primary_care: 195,
      chronic_disease: 235,
      preventive: 160,
      specialist: 340,
      womens_health: 255,
      paediatric: 185,
      mental_health: 215
    }
  },
  {
    locationId: "us-ga-001",
    name: "HealthCore Atlanta",
    city: "Atlanta",
    stateOrCountry: "GA",
    country: "US",
    phone: "(404) 330-9900",
    averageConsultationFee: {
      primary_care: 170,
      chronic_disease: 210,
      preventive: 145,
      specialist: 310,
      womens_health: 230,
      paediatric: 165,
      mental_health: 190
    }
  }
];
var knownLocationIds = sampleLocations.map((location) => location.locationId);
var sampleClaims = [
  {
    claimId: "CLM-000001",
    patientId: "HC-A3F291",
    locationId: "us-tx-001",
    serviceType: "primary_care",
    payerName: "BlueCross",
    payerId: "BC001",
    submissionDate: "2025-03-10",
    claimAmount: 180,
    status: "approved",
    resubmitted: false
  },
  {
    claimId: "CLM-000002",
    patientId: "HC-B7K442",
    locationId: "us-fl-001",
    serviceType: "specialist",
    payerName: "Aetna",
    payerId: "AET002",
    submissionDate: "2025-03-11",
    claimAmount: 340,
    status: "denied",
    denialReason: "missing_authorisation",
    resubmitted: false
  },
  {
    claimId: "CLM-000003",
    patientId: "HC-C2M881",
    locationId: "us-ga-001",
    serviceType: "chronic_disease",
    payerName: "Medicare",
    payerId: "MED003",
    submissionDate: "2025-03-12",
    claimAmount: 210,
    status: "approved",
    resubmitted: false
  },
  {
    claimId: "CLM-000004",
    patientId: "HC-D9P553",
    locationId: "us-tx-001",
    serviceType: "preventive",
    payerName: "BlueCross",
    payerId: "BC001",
    submissionDate: "2025-03-13",
    claimAmount: 150,
    status: "denied",
    denialReason: "coding_error",
    resubmitted: true
  },
  {
    claimId: "CLM-000005",
    patientId: "HC-E4Q117",
    locationId: "us-fl-001",
    serviceType: "mental_health",
    payerName: "Cigna",
    payerId: "CIG004",
    submissionDate: "2025-03-14",
    claimAmount: 215,
    status: "pending",
    resubmitted: false
  }
];
var sampleAppointments = [
  {
    appointmentId: "APT-000001",
    patientId: "HC-A3F291",
    locationId: "us-tx-001",
    serviceType: "primary_care",
    scheduledDate: "2025-03-10",
    scheduledTime: "09:00",
    status: "completed",
    confirmedAt: "2025-03-09T14:00:00Z"
  },
  {
    appointmentId: "APT-000002",
    patientId: "HC-F6R228",
    locationId: "us-fl-001",
    serviceType: "specialist",
    scheduledDate: "2025-03-11",
    scheduledTime: "11:30",
    status: "no_show",
    noShowReason: "Patient did not call to cancel"
  },
  {
    appointmentId: "APT-000003",
    patientId: "HC-G1S774",
    locationId: "us-tx-001",
    serviceType: "chronic_disease",
    scheduledDate: "2025-03-12",
    scheduledTime: "14:00",
    status: "no_show",
    noShowReason: "Unreachable before appointment"
  },
  {
    appointmentId: "APT-000004",
    patientId: "HC-H8T390",
    locationId: "us-ga-001",
    serviceType: "preventive",
    scheduledDate: "2025-03-13",
    scheduledTime: "10:00",
    status: "completed",
    confirmedAt: "2025-03-12T09:30:00Z"
  },
  {
    appointmentId: "APT-000005",
    patientId: "HC-I5U661",
    locationId: "us-fl-001",
    serviceType: "mental_health",
    scheduledDate: "2025-03-14",
    scheduledTime: "16:00",
    status: "no_show",
    noShowReason: "Transportation issue reported"
  }
];
var sampleClinicians = [
  {
    clinicianId: "CLN-000001",
    firstName: "Marcus",
    lastName: "Reid",
    role: "physician",
    locationId: "us-tx-001",
    licenceState: "TX",
    licenceExpiryDate: "2026-06-30",
    cmeHoursRequired: 40,
    cmeHoursLogged: 28,
    cmeYearStartDate: "2025-01-01"
  },
  {
    clinicianId: "CLN-000002",
    firstName: "Sandra",
    lastName: "Flores",
    role: "nurse_practitioner",
    locationId: "us-fl-001",
    licenceState: "FL",
    licenceExpiryDate: "2025-05-15",
    cmeHoursRequired: 30,
    cmeHoursLogged: 6,
    cmeYearStartDate: "2025-01-01"
  },
  {
    clinicianId: "CLN-000003",
    firstName: "David",
    lastName: "Okafor",
    role: "physician",
    locationId: "us-ga-001",
    licenceState: "GA",
    licenceExpiryDate: "2027-01-01",
    cmeHoursRequired: 40,
    cmeHoursLogged: 40,
    cmeYearStartDate: "2025-01-01"
  }
];

// ../../src/utils/collections.ts
var claimFilterEntries = (filters) => {
  return Object.entries(filters);
};
var claimFieldMatches = (claim, field, value) => {
  return claim[field] === value;
};
var compareByDirection = (first, second, direction) => {
  const result = first.localeCompare(second);
  return direction === "asc" ? result : -result;
};
var claimIdComparator = (direction) => {
  return (first, second) => compareByDirection(first.claimId, second.claimId, direction);
};
var appointmentDateComparator = (direction) => {
  return (first, second) => compareByDirection(first.scheduledDate, second.scheduledDate, direction);
};
var groupedBucket = (grouped, key) => {
  if (!grouped[key]) {
    grouped[key] = [];
  }
  return grouped[key];
};
var filterClaims = (claims, filters) => {
  const entries = claimFilterEntries(filters);
  return claims.filter((claim) => entries.every(([field, value]) => claimFieldMatches(claim, field, value)));
};
var filterAppointmentsByStatus = (appointments, status) => {
  return appointments.filter((appointment) => status.includes(appointment.status));
};
var sortClaimsById = (claims, direction) => {
  return [...claims].sort(claimIdComparator(direction));
};
var sortAppointmentsByDate = (appointments, direction) => {
  return [...appointments].sort(appointmentDateComparator(direction));
};
var groupClaimsBy = (claims, key) => {
  return claims.reduce((grouped, claim) => {
    const groupKey = claim[key];
    groupedBucket(grouped, groupKey).push(claim);
    return grouped;
  }, {});
};

// ../../src/utils/search.ts
var middleIndex = (left, right) => {
  return Math.floor((left + right) / 2);
};
var findClaimById = (claims, claimId) => {
  const match = claims.find((claim) => claim.claimId === claimId);
  return match ?? null;
};
var findClinicianById = (clinicians, clinicianId) => {
  const match = clinicians.find((clinician) => clinician.clinicianId === clinicianId);
  return match ?? null;
};
var binarySearchClaimById = (sortedClaims, targetId) => {
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

// ../../src/utils/transformations.ts
var MS_PER_DAY = 24 * 60 * 60 * 1e3;
var parseDate = (dateValue) => {
  return /* @__PURE__ */ new Date(`${dateValue}T00:00:00Z`);
};
var roundToTwo = (value) => {
  return Number(value.toFixed(2));
};
var roundToOne = (value) => {
  return Number(value.toFixed(1));
};
var percentage = (part, whole) => {
  if (whole === 0) {
    return 0;
  }
  return part / whole * 100;
};
var calendarDayDiff = (fromDate, toDate) => {
  const from = parseDate(fromDate);
  const to = parseDate(toDate);
  return Math.ceil((to.getTime() - from.getTime()) / MS_PER_DAY);
};
var groupCount = (items, keyFn) => {
  return items.reduce((acc, item) => {
    const key = keyFn(item);
    if (!acc[key]) {
      acc[key] = [];
    }
    acc[key].push(item);
    return acc;
  }, {});
};
var deniedClaims = (claims) => {
  return claims.filter((claim) => claim.status === "denied");
};
var rateFromClaims = (claims) => {
  return roundToTwo(percentage(deniedClaims(claims).length, claims.length));
};
var dateInInclusiveRange = (dateValue, start, end) => {
  const date = parseDate(dateValue).getTime();
  const rangeStart = parseDate(start).getTime();
  const rangeEnd = parseDate(end).getTime();
  return date >= rangeStart && date <= rangeEnd;
};
var weekStartDate = (weekEndingDate) => {
  const end = parseDate(weekEndingDate);
  const start = new Date(end.getTime() - 6 * MS_PER_DAY);
  return start.toISOString().slice(0, 10);
};
var isNoShow = (appointment) => {
  return appointment.status === "no_show";
};
var noShowAppointments = (appointments) => {
  return appointments.filter(isNoShow);
};
var appointmentInWeekWindow = (appointment, start, end) => {
  return dateInInclusiveRange(appointment.scheduledDate, start, end);
};
var cycleEndDate = (cycleStartDate) => {
  const start = parseDate(cycleStartDate);
  const end = new Date(Date.UTC(start.getUTCFullYear() + 1, start.getUTCMonth(), start.getUTCDate() - 1));
  return end.toISOString().slice(0, 10);
};
var totalCycleDays = (cycleStartDate) => {
  const cycleEnd = cycleEndDate(cycleStartDate);
  return calendarDayDiff(cycleStartDate, cycleEnd) + 1;
};
var elapsedCycleDays = (cycleStartDate, asOfDate) => {
  const elapsed = calendarDayDiff(cycleStartDate, asOfDate) + 1;
  if (elapsed < 0) {
    return 0;
  }
  return elapsed;
};
var elapsedCyclePercent = (cycleStartDate, asOfDate) => {
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
var clinicianPercentComplete = (required, logged) => {
  if (required === 0) {
    return 100;
  }
  return roundToOne(percentage(logged, required));
};
var statusForClinician = (hoursRequired, hoursLogged, cycleStartDate, asOfDate) => {
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
var calculateDenialRate = (claims) => {
  if (claims.length === 0) {
    throw new Error("Claims array cannot be empty.");
  }
  return rateFromClaims(claims);
};
var denialRateByPayer = (claims) => {
  const grouped = groupCount(claims, (claim) => claim.payerName);
  return Object.fromEntries(
    Object.entries(grouped).map(([payerName, payerClaims]) => [payerName, rateFromClaims(payerClaims)])
  );
};
var denialRateByLocation = (claims) => {
  const grouped = groupCount(claims, (claim) => claim.locationId);
  return Object.fromEntries(
    Object.entries(grouped).map(([locationId, locationClaims]) => [locationId, rateFromClaims(locationClaims)])
  );
};
var flagHighDenialPayers = (claims, threshold = 8) => {
  const rates = denialRateByPayer(claims);
  return Object.entries(rates).filter(([, rate]) => rate > threshold).map(([payerName]) => payerName);
};
var calculateNoShowCost = (appointments, location, weekEndingDate) => {
  const rangeStart = weekStartDate(weekEndingDate);
  const rangeEnd = weekEndingDate;
  const total = appointments.filter((appointment) => appointment.locationId === location.locationId).filter(isNoShow).filter((appointment) => appointmentInWeekWindow(appointment, rangeStart, rangeEnd)).reduce((sum, appointment) => sum + location.averageConsultationFee[appointment.serviceType], 0);
  return roundToTwo(total);
};
var noShowRateByLocation = (appointments) => {
  const grouped = groupCount(appointments, (appointment) => appointment.locationId);
  return Object.fromEntries(
    Object.entries(grouped).map(([locationId, locationAppointments]) => {
      const rate = percentage(noShowAppointments(locationAppointments).length, locationAppointments.length);
      return [locationId, roundToTwo(rate)];
    })
  );
};
var flagHighNoShowLocations = (appointments, threshold = 20) => {
  const rates = noShowRateByLocation(appointments);
  return Object.entries(rates).filter(([, rate]) => rate > threshold).map(([locationId]) => locationId);
};
var generateCMEReport = (clinicians, asOfDate) => {
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
      licenceDaysRemaining: calendarDayDiff(asOfDate, clinician.licenceExpiryDate)
    };
  });
};
var getCliniciansAtRisk = (clinicians, asOfDate) => {
  const atRiskIds = new Set(
    generateCMEReport(clinicians, asOfDate).filter((entry) => entry.complianceStatus === "at_risk" || entry.complianceStatus === "overdue").map((entry) => entry.clinicianId)
  );
  return clinicians.filter((clinician) => atRiskIds.has(clinician.clinicianId));
};
var getCliniciansWithExpiringLicences = (clinicians, asOfDate, daysThreshold) => {
  return clinicians.filter((clinician) => {
    const daysRemaining = calendarDayDiff(asOfDate, clinician.licenceExpiryDate);
    return daysRemaining >= 0 && daysRemaining <= daysThreshold;
  });
};

// ../../src/utils/validations.ts
var isValidDate = (dateValue) => {
  const parsed = new Date(dateValue);
  return !Number.isNaN(parsed.getTime());
};
var todayIsoDate = () => {
  return (/* @__PURE__ */ new Date()).toISOString().slice(0, 10);
};
var isFutureDate = (dateValue) => {
  return dateValue > todayIsoDate();
};
var isPatientIdFormatValid = (patientId) => {
  return /^HC-[A-Za-z0-9]{6}$/.test(patientId);
};
var hasValidClaimAmount = (amount) => {
  return amount > 0;
};
var isKnownLocation = (locationId, knownLocationIds2) => {
  return knownLocationIds2.includes(locationId);
};
var hasDenialReasonWhenDenied = (claim) => {
  if (claim.status !== "denied") {
    return true;
  }
  return Boolean(claim.denialReason);
};
var nonNegative = (value) => {
  return value >= 0;
};
var validClinicianRoles = ["physician", "nurse_practitioner", "nurse", "medical_assistant"];
var hasValidClinicianRole = (role) => {
  return validClinicianRoles.includes(role);
};
var dateIsTodayOrLater = (dateValue) => {
  return dateValue >= todayIsoDate();
};
var addError = (errors, condition, message) => {
  if (!condition) {
    errors.push(message);
  }
};
var validateClaim = (claim, knownLocationIds2) => {
  const errors = [];
  addError(errors, hasValidClaimAmount(claim.claimAmount), "claimAmount must be greater than 0.");
  addError(errors, isValidDate(claim.submissionDate), "submissionDate must be a valid date.");
  addError(
    errors,
    !isFutureDate(claim.submissionDate),
    "submissionDate must not be a future date."
  );
  addError(
    errors,
    isKnownLocation(claim.locationId, knownLocationIds2),
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
    errors
  };
};
var validateClinician = (clinician) => {
  const errors = [];
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
    errors
  };
};
var isDenialRateAboveThreshold = (rate, threshold = 8) => {
  return rate > threshold;
};
var isNoShowRateAboveThreshold = (rate, threshold = 20) => {
  return rate > threshold;
};

// main.ts
var getElement = (id) => {
  const element = document.getElementById(id);
  if (!element) {
    throw new Error(`Element with id '${id}' was not found.`);
  }
  return element;
};
var writeJson = (id, data) => {
  getElement(id).textContent = JSON.stringify(data, null, 2);
};
var bindClick = (id, onClick) => {
  getElement(id).addEventListener("click", onClick);
};
var renderCollectionsSection = () => {
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
var renderSearchSection = () => {
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
var renderTransformationSection = () => {
  bindClick("btn-denial-rates", () => {
    const denialRate = calculateDenialRate(sampleClaims);
    writeJson("out-transformations", {
      denialRate,
      denialRateByPayer: denialRateByPayer(sampleClaims),
      denialRateByLocation: denialRateByLocation(sampleClaims),
      highDenialPayersAbove8: flagHighDenialPayers(sampleClaims),
      denialRateAboveDefaultThreshold: isDenialRateAboveThreshold(denialRate)
    });
  });
  bindClick("btn-no-show", () => {
    const noShowRates = noShowRateByLocation(sampleAppointments);
    writeJson("out-transformations", {
      noShowRateByLocation: noShowRates,
      filteredNoShows: filterAppointmentsByStatus(sampleAppointments, ["no_show"]),
      noShowCostMiami: calculateNoShowCost(sampleAppointments, sampleLocations[1], "2025-03-14"),
      highNoShowLocationsAbove20: flagHighNoShowLocations(sampleAppointments),
      miamiNoShowRateAboveDefaultThreshold: isNoShowRateAboveThreshold(noShowRates["us-fl-001"] ?? 0)
    });
  });
};
var renderValidationSection = () => {
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
      )
    });
  });
  bindClick("btn-validations", () => {
    const invalidRoleClinician = {
      ...sampleClinicians[0],
      role: "invalid_role"
    };
    writeJson("out-validation", {
      claimValidation: validateClaim(sampleClaims[1], knownLocationIds),
      clinicianValidation: validateClinician(sampleClinicians[0]),
      invalidClinicianRoleValidation: validateClinician(invalidRoleClinician)
    });
  });
};
var renderReadyState = () => {
  writeJson("out-collections", { status: "Ready", section: "Collections" });
  writeJson("out-search", { status: "Ready", section: "Search" });
  writeJson("out-transformations", { status: "Ready", section: "Transformations" });
  writeJson("out-validation", { status: "Ready", section: "CME and Validation" });
};
var bootstrap = () => {
  renderCollectionsSection();
  renderSearchSection();
  renderTransformationSection();
  renderValidationSection();
  renderReadyState();
};
bootstrap();
