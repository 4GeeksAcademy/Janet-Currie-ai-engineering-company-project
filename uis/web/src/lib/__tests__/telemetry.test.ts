import {
  EVENT_ALLOWLISTS,
  countryCode,
  mapProductCategory,
  resetTelemetryForTests,
  sanitizeProperties,
  setTelemetryUserId,
  telemetryQueueLength,
  track,
} from "@/lib/telemetry";

describe("telemetry sanitizeProperties", () => {
  it("drops keys outside the allowlist and never keeps email", () => {
    const props = sanitizeProperties("inbound_order_created", {
      clinic_id: 1,
      country: "US",
      product_id: "9",
      product_category: "ppe",
      quantity: 2,
      email: "nurse@healthcore.example",
      extra: "nope",
    });
    expect(props).toEqual({
      clinic_id: 1,
      country: "US",
      product_id: "9",
      product_category: "ppe",
      quantity: 2,
    });
    expect(props).not.toHaveProperty("email");
  });

  it("maps inventory categories to HealthCore allowlist values", () => {
    expect(mapProductCategory("ppe")).toBe("ppe");
    expect(mapProductCategory("medications")).toBe("medication");
    expect(mapProductCategory("wound_care")).toBe("consumable");
    expect(countryCode("UK")).toBe("UK");
  });

  it("defines allowlists for every mandatory event", () => {
    for (const name of [
      "inbound_order_created",
      "outbound_order_created",
      "stock_threshold_triggered",
      "direct_stock_edit_rejected",
      "supply_expiry_flagged",
    ]) {
      expect(EVENT_ALLOWLISTS[name]?.length).toBeGreaterThan(0);
    }
  });
});

describe("track queue", () => {
  beforeEach(() => {
    resetTelemetryForTests();
    window.sessionStorage.clear();
    setTelemetryUserId("99");
  });

  it("enqueues a capture-time envelope without caller envelope fields", () => {
    track("page_viewed", { route: "/operations", eventId: "caller-must-not-win" });
    expect(telemetryQueueLength()).toBe(1);
  });

  it("does not enqueue unknown event types", () => {
    track("not_in_catalogue", { email: "a@b.c", password: "secret" });
    expect(telemetryQueueLength()).toBe(0);
  });
});
