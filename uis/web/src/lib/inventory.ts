import { apiFetch, parseError, readJson } from "@/lib/apiClient";

export const INSUFFICIENT_STOCK_PREFIX = "Insufficient stock for supply";

export class InsufficientStockError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "InsufficientStockError";
  }
}

export type SupplyCategory =
  | "ppe"
  | "wound_care"
  | "diagnostics"
  | "medications"
  | "consumables";

export type ConsumptionType = "clinical_use" | "expiry_waste";
export type OrderKind = "inbound" | "outbound";
export type StockLevel = "out" | "low" | "healthy";

export type MedicalSupply = {
  id: number;
  name: string;
  sku: string;
  category: SupplyCategory | string;
  unit: string;
  country: "US" | "UK" | string;
  current_stock: number;
};

export type SupplySummary = {
  id: number;
  name: string;
  sku: string;
  category: string;
  unit: string;
  country: string;
};

export type DeliveryCreate = {
  supply_id: number;
  quantity: number;
  vendor_name: string;
  clinic_id: number;
};

export type ConsumptionCreate = {
  supply_id: number;
  quantity: number;
  consumption_type: ConsumptionType;
  clinic_id: number;
};

export type OrderMovement = {
  kind: OrderKind;
  id: number;
  supply_id: number;
  quantity: number;
  clinic_id: number;
  created_at: string;
  user_uuid: string;
  vendor_name: string | null;
  consumption_type: string | null;
  supply: SupplySummary;
};

export const CLINIC_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12] as const;

export function isClinicId(n: number): boolean {
  return Number.isInteger(n) && n >= 1 && n <= 12;
}

export const CATEGORY_LABELS: Record<string, string> = {
  ppe: "PPE",
  wound_care: "Wound care",
  diagnostics: "Diagnostics",
  medications: "Medications",
  consumables: "Consumables",
};

export const CONSUMPTION_LABELS: Record<ConsumptionType, string> = {
  clinical_use: "Clinical use",
  expiry_waste: "Expiry waste",
};

export function categoryLabel(category: string): string {
  return CATEGORY_LABELS[category] ?? category;
}

/**
 * Weekly clinic restock: 0 = cannot issue; 1–24 = below a typical case-equivalent;
 * 25+ = healthy. Seed gloves (105) stay healthy.
 */
export function stockStatus(n: number): StockLevel {
  if (n <= 0) return "out";
  if (n <= 24) return "low";
  return "healthy";
}

export function stockStatusLabel(level: StockLevel): string {
  if (level === "out") return "Out of stock";
  if (level === "low") return "Low stock";
  return "In stock";
}

export function formatInventoryDate(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return new Intl.DateTimeFormat("en-GB", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

export function movementTypeLabel(row: OrderMovement): string {
  if (row.kind === "inbound") return "Delivery (inbound)";
  if (row.consumption_type === "expiry_waste") return "Expiry waste (outbound)";
  if (row.consumption_type === "clinical_use") return "Clinical use (outbound)";
  return "Consumption (outbound)";
}

async function throwIfNotOk(response: Response): Promise<void> {
  if (response.ok) return;
  if (response.status === 400) {
    const copy = response.clone();
    const payload = (await copy.json().catch(() => ({}))) as Record<string, unknown>;
    if (
      typeof payload.detail === "string" &&
      payload.detail.startsWith(INSUFFICIENT_STOCK_PREFIX)
    ) {
      throw new InsufficientStockError(payload.detail);
    }
  }
  await parseError(response);
}

export async function listSupplies(): Promise<MedicalSupply[]> {
  const response = await apiFetch("/inventory/products");
  await throwIfNotOk(response);
  return readJson<MedicalSupply[]>(response);
}

export async function getSupply(
  id: number,
  options: { signal?: AbortSignal } = {},
): Promise<MedicalSupply> {
  const response = await apiFetch(`/inventory/products/${id}`, { signal: options.signal });
  await throwIfNotOk(response);
  return readJson<MedicalSupply>(response);
}

export async function createDelivery(input: DeliveryCreate): Promise<void> {
  const body: DeliveryCreate = {
    supply_id: input.supply_id,
    quantity: input.quantity,
    vendor_name: input.vendor_name,
    clinic_id: input.clinic_id,
  };
  const response = await apiFetch("/inventory/orders/inbound", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await throwIfNotOk(response);
}

export async function createConsumption(input: ConsumptionCreate): Promise<void> {
  const body: ConsumptionCreate = {
    supply_id: input.supply_id,
    quantity: input.quantity,
    consumption_type: input.consumption_type,
    clinic_id: input.clinic_id,
  };
  const response = await apiFetch("/inventory/orders/outbound", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  await throwIfNotOk(response);
}

export async function listMovements(): Promise<OrderMovement[]> {
  const response = await apiFetch("/inventory/orders");
  await throwIfNotOk(response);
  return readJson<OrderMovement[]>(response);
}
