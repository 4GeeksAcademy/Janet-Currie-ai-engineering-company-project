import {
  apiFetch,
  ApiTimeoutError,
  ApiValidationError,
  getAccessToken,
  setAccessToken,
} from "@/lib/apiClient";
import {
  InsufficientStockError,
  createConsumption,
  createDelivery,
  deriveMovementRows,
  getSupply,
  listMovements,
  listSupplies,
  movementTypeLabel,
  stockStatus,
  stockStatusLabel,
  type OrderMovement,
} from "@/lib/inventory";

const gloves = {
  id: 1,
  name: "Nitrile gloves (box of 100)",
  sku: "HCR-PPE-001",
  category: "ppe",
  unit: "box",
  country: "US",
  current_stock: 105,
};

function jsonResponse(status: number, body: unknown): Response {
  const payload = {
    ok: status >= 200 && status < 300,
    status,
    clone() {
      return jsonResponse(status, body);
    },
    json: async () => body,
    headers: { get: () => "application/json" },
  };
  return payload as unknown as Response;
}

describe("stockStatus", () => {
  it("labels out, low, and healthy bands", () => {
    expect(stockStatus(0)).toBe("out");
    expect(stockStatusLabel("out")).toBe("Out of stock");
    expect(stockStatus(24)).toBe("low");
    expect(stockStatus(25)).toBe("healthy");
    expect(stockStatus(105)).toBe("healthy");
  });
});

const movementGloves = {
  id: 1,
  name: "Nitrile gloves (box of 100)",
  sku: "HCR-PPE-001",
  category: "ppe",
  unit: "box",
  country: "US",
};

function movement(
  partial: Partial<OrderMovement> & Pick<OrderMovement, "id" | "kind" | "created_at">,
): OrderMovement {
  return {
    supply_id: 1,
    quantity: 1,
    clinic_id: 1,
    user_uuid: "1",
    vendor_name: partial.kind === "inbound" ? "MedLine" : null,
    consumption_type: partial.kind === "outbound" ? "clinical_use" : null,
    supply: movementGloves,
    ...partial,
  };
}

describe("deriveMovementRows", () => {
  it("returns an empty list for empty input", () => {
    expect(deriveMovementRows([])).toEqual([]);
  });

  it("sorts newest first and maps labels", () => {
    const older = movement({ id: 1, kind: "inbound", created_at: "2026-01-01T00:00:00Z", quantity: 10 });
    const newer = movement({
      id: 2,
      kind: "outbound",
      created_at: "2026-02-01T00:00:00Z",
      quantity: 3,
      consumption_type: "expiry_waste",
    });
    const rows = deriveMovementRows([older, newer]);
    expect(rows.map((row) => row.key)).toEqual(["outbound-2", "inbound-1"]);
    expect(rows[0].typeLabel).toBe("Expiry waste (outbound)");
    expect(rows[1].quantityLabel).toBe("10 box");
  });

  it("does not mutate the source array when reordering", () => {
    const older = movement({ id: 1, kind: "inbound", created_at: "2026-01-01T00:00:00Z" });
    const newer = movement({ id: 2, kind: "inbound", created_at: "2026-03-01T00:00:00Z" });
    const source = [older, newer];
    deriveMovementRows(source);
    expect(source.map((row) => row.id)).toEqual([1, 2]);
  });

  it("replaces rows when the input set changes", () => {
    const first = deriveMovementRows([
      movement({ id: 1, kind: "inbound", created_at: "2026-01-01T00:00:00Z" }),
    ]);
    const next = deriveMovementRows([
      movement({ id: 9, kind: "outbound", created_at: "2026-04-01T00:00:00Z" }),
    ]);
    expect(first[0].key).toBe("inbound-1");
    expect(next[0].key).toBe("outbound-9");
  });
});

describe("inventory API helpers", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    window.localStorage.clear();
    setAccessToken("jwt-test-token");
    global.fetch = jest.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("lists supplies with bearer token and configured base URL", async () => {
    (global.fetch as jest.Mock).mockResolvedValue(jsonResponse(200, [gloves]));
    const rows = await listSupplies();
    expect(rows[0].current_stock).toBe(105);
    const [url, init] = (global.fetch as jest.Mock).mock.calls[0];
    expect(url).toBe("http://localhost:8000/inventory/products");
    expect(init.headers.get("Authorization")).toBe("Bearer jwt-test-token");
    expect(getAccessToken()).toBe("jwt-test-token");
  });

  it("loads one supply by id", async () => {
    (global.fetch as jest.Mock).mockResolvedValue(jsonResponse(200, gloves));
    await getSupply(1);
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toBe(
      "http://localhost:8000/inventory/products/1",
    );
  });

  it("posts delivery and consumption payloads without UI or server-owned fields", async () => {
    (global.fetch as jest.Mock).mockResolvedValue(jsonResponse(201, {}));
    await createDelivery({
      supply_id: 1,
      quantity: 4,
      vendor_name: "MedLine Industries",
      clinic_id: 2,
    });
    await createConsumption({
      supply_id: 1,
      quantity: 2,
      consumption_type: "clinical_use",
      clinic_id: 1,
    });
    const inbound = JSON.parse((global.fetch as jest.Mock).mock.calls[0][1].body);
    const outbound = JSON.parse((global.fetch as jest.Mock).mock.calls[1][1].body);
    expect(inbound).toEqual({
      supply_id: 1,
      quantity: 4,
      vendor_name: "MedLine Industries",
      clinic_id: 2,
    });
    expect(inbound).not.toHaveProperty("user_uuid");
    expect(inbound).not.toHaveProperty("current_stock");
    expect(outbound).toEqual({
      supply_id: 1,
      quantity: 2,
      consumption_type: "clinical_use",
      clinic_id: 1,
    });
    expect((global.fetch as jest.Mock).mock.calls[0][0]).toContain("/inventory/orders/inbound");
    expect((global.fetch as jest.Mock).mock.calls[1][0]).toContain("/inventory/orders/outbound");
  });

  it("maps history rows and labels both movement kinds", async () => {
    (global.fetch as jest.Mock).mockResolvedValue(
      jsonResponse(200, [
        {
          kind: "inbound",
          id: 1,
          supply_id: 1,
          quantity: 100,
          clinic_id: 1,
          created_at: "2026-01-01T00:00:00Z",
          user_uuid: "1",
          vendor_name: "MedLine Industries",
          consumption_type: null,
          supply: gloves,
        },
        {
          kind: "outbound",
          id: 2,
          supply_id: 1,
          quantity: 25,
          clinic_id: 1,
          created_at: "2026-01-02T00:00:00Z",
          user_uuid: "1",
          vendor_name: null,
          consumption_type: "clinical_use",
          supply: gloves,
        },
      ]),
    );
    const rows = await listMovements();
    expect(movementTypeLabel(rows[0])).toBe("Delivery (inbound)");
    expect(movementTypeLabel(rows[1])).toBe("Clinical use (outbound)");
  });

  it("throws InsufficientStockError with the API message on outbound 400", async () => {
    const detail =
      "Insufficient stock for supply 'Nitrile gloves (box of 100)'. Available: 105, requested: 9999.";
    (global.fetch as jest.Mock).mockResolvedValue(jsonResponse(400, { detail }));
    await expect(
      createConsumption({
        supply_id: 1,
        quantity: 9999,
        consumption_type: "clinical_use",
        clinic_id: 1,
      }),
    ).rejects.toEqual(expect.objectContaining({ name: "InsufficientStockError", message: detail }));
  });

  it("does not treat a generic 400 as insufficient stock", async () => {
    (global.fetch as jest.Mock).mockResolvedValue(jsonResponse(400, { detail: "nope" }));
    await expect(
      createDelivery({ supply_id: 1, quantity: 1, vendor_name: "X", clinic_id: 1 }),
    ).rejects.not.toBeInstanceOf(InsufficientStockError);
  });

  it("keeps 401 distinguishable from 400", async () => {
    (global.fetch as jest.Mock).mockResolvedValue(jsonResponse(401, { detail: "Could not validate credentials" }));
    await expect(listSupplies()).rejects.toMatchObject({ status: 401 });
  });

  it("maps 5xx without leaking detail", async () => {
    (global.fetch as jest.Mock).mockResolvedValue(jsonResponse(500, { detail: "SECRET leaked" }));
    await expect(listSupplies()).rejects.toMatchObject({ status: 500 });
  });

  it("turns non-JSON error bodies into application errors", async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: false,
      status: 500,
      clone() {
        return this;
      },
      json: async () => {
        throw new Error("no json");
      },
    });
    await expect(listSupplies()).rejects.toBeTruthy();
  });

  it("maps 422 to ApiValidationError", async () => {
    (global.fetch as jest.Mock).mockResolvedValue(
      jsonResponse(422, { errors: [{ field: "quantity", message: "must be positive" }] }),
    );
    await expect(
      createDelivery({ supply_id: 1, quantity: 0, vendor_name: "X", clinic_id: 1 }),
    ).rejects.toBeInstanceOf(ApiValidationError);
  });

  it("propagates network failures", async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(listSupplies()).rejects.toBeInstanceOf(TypeError);
  });

  it("passes an abort signal through getSupply", async () => {
    const controller = new AbortController();
    (global.fetch as jest.Mock).mockResolvedValue(jsonResponse(200, gloves));
    await getSupply(3, { signal: controller.signal });
    expect((global.fetch as jest.Mock).mock.calls[0][1].signal).toBeInstanceOf(AbortSignal);
  });
});

describe("apiFetch abort vs timeout", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("rethrows when the caller aborts", async () => {
    const controller = new AbortController();
    global.fetch = jest.fn((_url, init?: RequestInit) => {
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    });
    const pending = apiFetch("/inventory/products", { signal: controller.signal, timeoutMs: 30_000 });
    controller.abort();
    await expect(pending).rejects.toMatchObject({ name: "AbortError" });
  });

  it("maps timeout abort to ApiTimeoutError", async () => {
    global.fetch = jest.fn((_url, init?: RequestInit) => {
      return new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    });
    await expect(apiFetch("/inventory/products", { timeoutMs: 20 })).rejects.toBeInstanceOf(
      ApiTimeoutError,
    );
  });
});
