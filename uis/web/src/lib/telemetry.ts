export const TELEMETRY_SCHEMA_VERSION = "1.0.0";
export const TELEMETRY_FLUSH_MS = 10_000;
export const TELEMETRY_MAX_BATCH = 20;
export const TELEMETRY_MAX_RETRIES = 3;

const FORBIDDEN_PROPERTY_KEYS = new Set([
  "email",
  "name",
  "password",
  "hashed_password",
  "token",
  "access_token",
]);

export const EVENT_ALLOWLISTS: Record<string, readonly string[]> = {
  inbound_order_created: [
    "clinic_id",
    "country",
    "product_id",
    "product_category",
    "quantity",
  ],
  outbound_order_created: [
    "clinic_id",
    "country",
    "product_id",
    "product_category",
    "quantity",
    "department",
  ],
  stock_threshold_triggered: [
    "clinic_id",
    "country",
    "product_id",
    "product_category",
    "quantity",
  ],
  direct_stock_edit_rejected: [
    "clinic_id",
    "country",
    "product_id",
    "product_category",
    "quantity",
  ],
  supply_expiry_flagged: [
    "clinic_id",
    "country",
    "product_id",
    "product_category",
    "quantity",
  ],
  inbound_order_validation_failed: [
    "clinic_id",
    "country",
    "product_id",
    "product_category",
    "quantity",
    "reason",
  ],
  outbound_order_rejected: [
    "clinic_id",
    "country",
    "product_id",
    "product_category",
    "quantity",
    "reason",
  ],
  user_login_failed: ["reason"],
  user_login_succeeded: [],
  session_expired: ["reason"],
  page_viewed: ["route"],
  api_latency_recorded: ["route", "duration_ms", "status"],
  frontend_error_raised: ["route", "message"],
  web_vital_recorded: ["route", "name", "value"],
};

export type TelemetryEventEnvelope = {
  eventId: string;
  timestamp: string;
  sessionId: string;
  userId: string;
  event_type: string;
  schemaVersion: string;
  requestId: string;
  properties: Record<string, unknown>;
};

type TrackProperties = Record<string, unknown>;

let queue: TelemetryEventEnvelope[] = [];
let sessionId = "";
let userId = "anonymous";
let flushTimer: ReturnType<typeof setInterval> | null = null;
let sending = false;
let visibilityBound = false;
let listenersBound = false;

function telemetryUrl(): string {
  const raw = process.env.NEXT_PUBLIC_TELEMETRY_ENDPOINT?.replace(/\/$/, "");
  return raw || "http://localhost:8000/telemetry/events";
}

function uuid(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function ensureSessionId(): string {
  if (sessionId) return sessionId;
  if (typeof window !== "undefined") {
    const existing = window.sessionStorage.getItem("healthcore_telemetry_session");
    if (existing) {
      sessionId = existing;
      return sessionId;
    }
    sessionId = uuid();
    window.sessionStorage.setItem("healthcore_telemetry_session", sessionId);
    return sessionId;
  }
  sessionId = uuid();
  return sessionId;
}

export function setTelemetryUserId(next: string | null): void {
  userId = next && next.trim() ? next : "anonymous";
}

export function sanitizeProperties(
  eventType: string,
  properties: TrackProperties,
): Record<string, unknown> {
  const allow = EVENT_ALLOWLISTS[eventType];
  const out: Record<string, unknown> = {};
  if (!allow) return out;
  for (const key of allow) {
    if (!(key in properties)) continue;
    if (FORBIDDEN_PROPERTY_KEYS.has(key)) continue;
    out[key] = properties[key];
  }
  return out;
}

export function mapProductCategory(category: string): "medication" | "ppe" | "consumable" | "equipment" {
  if (category === "ppe") return "ppe";
  if (category === "medications" || category === "medication") return "medication";
  if (category === "equipment") return "equipment";
  return "consumable";
}

export function countryCode(value: string): "US" | "UK" {
  return value === "UK" ? "UK" : "US";
}

export function inventoryProperties(input: {
  clinic_id: number;
  country: string;
  product_id: number | string;
  category: string;
  quantity: number;
  department?: string;
}): Record<string, unknown> {
  const props: Record<string, unknown> = {
    clinic_id: input.clinic_id,
    country: countryCode(input.country),
    product_id: String(input.product_id),
    product_category: mapProductCategory(input.category),
    quantity: input.quantity,
  };
  if (input.department) props.department = input.department;
  return props;
}

export function opaqueUserIdFromToken(token: string | null): string | null {
  if (!token) return null;
  try {
    const part = token.split(".")[1];
    if (!part) return null;
    const normalized = part.replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(normalized)) as { sub?: unknown };
    return typeof payload.sub === "string" && payload.sub ? payload.sub : null;
  } catch {
    return null;
  }
}

async function postBatch(events: TelemetryEventEnvelope[]): Promise<boolean> {
  const body = JSON.stringify({ events });
  const url = telemetryUrl();
  try {
    const response = await fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body,
      keepalive: true,
    });
    return response.ok;
  } catch {
    return false;
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, ms);
  });
}

export async function flushTelemetry(): Promise<void> {
  if (sending || queue.length === 0) return;
  sending = true;
  const batch = queue.splice(0, TELEMETRY_MAX_BATCH);
  let delay = 250;
  let ok = false;
  try {
    for (let attempt = 0; attempt < TELEMETRY_MAX_RETRIES; attempt += 1) {
      ok = await postBatch(batch);
      if (ok) break;
      await sleep(delay);
      delay *= 2;
    }
    if (!ok) {
      return;
    }
  } finally {
    sending = false;
  }
}

function enqueue(event: TelemetryEventEnvelope): void {
  queue.push(event);
  if (queue.length >= TELEMETRY_MAX_BATCH) {
    void flushTelemetry();
  }
}

export function track(eventType: string, properties: TrackProperties = {}): void {
  if (typeof window === "undefined") return;
  if (!(eventType in EVENT_ALLOWLISTS)) return;
  startTelemetry();
  enqueue({
    eventId: uuid(),
    timestamp: new Date().toISOString(),
    sessionId: ensureSessionId(),
    userId,
    event_type: eventType,
    schemaVersion: TELEMETRY_SCHEMA_VERSION,
    requestId: uuid(),
    properties: sanitizeProperties(eventType, properties),
  });
}

function onVisibilityChange(): void {
  if (typeof document === "undefined" || document.visibilityState !== "hidden") return;
  if (queue.length === 0) return;
  const batch = queue.splice(0, queue.length);
  const body = JSON.stringify({ events: batch });
  const blob = new Blob([body], { type: "application/json" });
  if (typeof navigator !== "undefined" && typeof navigator.sendBeacon === "function") {
    navigator.sendBeacon(telemetryUrl(), blob);
    return;
  }
  void postBatch(batch);
}

export function startTelemetry(): void {
  if (typeof window === "undefined") return;
  ensureSessionId();
  if (!flushTimer) {
    flushTimer = setInterval(() => {
      void flushTelemetry();
    }, TELEMETRY_FLUSH_MS);
  }
  if (!visibilityBound) {
    document.addEventListener("visibilitychange", onVisibilityChange);
    visibilityBound = true;
  }
  if (!listenersBound) {
    window.addEventListener("error", (event) => {
      track("frontend_error_raised", {
        route: window.location.pathname,
        message: String(event.message ?? "error").slice(0, 200),
      });
    });
    window.addEventListener("unhandledrejection", (event) => {
      const reason = event.reason instanceof Error ? event.reason.message : String(event.reason);
      track("frontend_error_raised", {
        route: window.location.pathname,
        message: reason.slice(0, 200),
      });
    });
    listenersBound = true;
  }
}

export function recordLoadVital(): void {
  if (typeof window === "undefined" || typeof performance === "undefined") return;
  const nav = performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming | undefined;
  if (!nav) return;
  track("web_vital_recorded", {
    route: window.location.pathname,
    name: "load",
    value: Math.round(nav.loadEventEnd),
  });
}

export function resetTelemetryForTests(): void {
  queue = [];
  sessionId = "";
  userId = "anonymous";
  sending = false;
  if (flushTimer) {
    clearInterval(flushTimer);
    flushTimer = null;
  }
  visibilityBound = false;
  listenersBound = false;
}

export function telemetryQueueLength(): number {
  return queue.length;
}
