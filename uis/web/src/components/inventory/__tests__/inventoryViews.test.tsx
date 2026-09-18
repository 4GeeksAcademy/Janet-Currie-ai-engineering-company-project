import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MedicalSuppliesList } from "@/components/inventory/MedicalSuppliesList";
import { MovementHistory } from "@/components/inventory/MovementHistory";
import { SupplyConsumptionForm } from "@/components/inventory/SupplyConsumptionForm";
import { SupplyDeliveryForm } from "@/components/inventory/SupplyDeliveryForm";
import { InsufficientStockError, type MedicalSupply, type OrderMovement } from "@/lib/inventory";

jest.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(),
}));

jest.mock("@/lib/inventory", () => {
  const actual = jest.requireActual("@/lib/inventory");
  return {
    ...actual,
    listSupplies: jest.fn(),
    getSupply: jest.fn(),
    createDelivery: jest.fn(),
    createConsumption: jest.fn(),
    listMovements: jest.fn(),
  };
});

const inventory = jest.requireMock("@/lib/inventory") as {
  listSupplies: jest.Mock;
  getSupply: jest.Mock;
  createDelivery: jest.Mock;
  createConsumption: jest.Mock;
  listMovements: jest.Mock;
};

beforeEach(() => {
  inventory.listSupplies.mockReset();
  inventory.getSupply.mockReset();
  inventory.createDelivery.mockReset();
  inventory.createConsumption.mockReset();
  inventory.listMovements.mockReset();
});

const gloves: MedicalSupply = {
  id: 1,
  name: "Nitrile gloves (box of 100)",
  sku: "HCR-PPE-001",
  category: "ppe",
  unit: "box",
  country: "US",
  current_stock: 105,
};

describe("MedicalSuppliesList", () => {
  it("shows loading, then live stock and actions", async () => {
    inventory.listSupplies.mockResolvedValue([gloves]);
    render(<MedicalSuppliesList />);
    expect(screen.getByText("Loading medical supplies…")).toBeInTheDocument();
    expect(await screen.findByText("Nitrile gloves (box of 100)")).toBeInTheDocument();
    expect(screen.getByText(/105 box/)).toBeInTheDocument();
    expect(screen.getByText("In stock")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Record delivery" })).toHaveAttribute(
      "href",
      "/backoffice/inventory/orders/inbound?supply_id=1",
    );
  });

  it("shows an empty state when the catalogue is empty", async () => {
    inventory.listSupplies.mockResolvedValue([]);
    render(<MedicalSuppliesList />);
    expect(await screen.findByText("No medical supplies are on file yet.")).toBeInTheDocument();
  });

  it("shows a failed load with retry", async () => {
    inventory.listSupplies.mockRejectedValue(new Error("network"));
    render(<MedicalSuppliesList />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});

describe("SupplyDeliveryForm", () => {
  it("submits a delivery, disables while pending, and resets on success", async () => {
    const user = userEvent.setup();
    let resolveCreate: () => void = () => {};
    inventory.listSupplies.mockResolvedValue([gloves]);
    inventory.createDelivery.mockImplementation(
      () =>
        new Promise<void>((resolve) => {
          resolveCreate = resolve;
        }),
    );
    render(<SupplyDeliveryForm />);
    await screen.findByRole("option", { name: /Nitrile gloves/ });
    await user.selectOptions(screen.getByLabelText("Medical supply"), "1");
    await user.type(screen.getByLabelText("Quantity"), "3");
    await user.type(screen.getByLabelText("Vendor name"), "MedLine Industries");
    await user.click(screen.getByRole("button", { name: "Record delivery" }));
    expect(screen.getByRole("button", { name: "Recording…" })).toBeDisabled();
    resolveCreate();
    expect(await screen.findByText("Delivery recorded.")).toBeInTheDocument();
    expect(inventory.createDelivery).toHaveBeenCalledWith({
      supply_id: 1,
      quantity: 3,
      vendor_name: "MedLine Industries",
      clinic_id: 1,
    });
    expect(screen.getByLabelText("Quantity")).toHaveValue(null);
  });

  it("keeps entered fields after a failed submit", async () => {
    const user = userEvent.setup();
    inventory.listSupplies.mockResolvedValue([gloves]);
    inventory.createDelivery.mockRejectedValue(new Error("fail"));
    render(<SupplyDeliveryForm />);
    await screen.findByRole("option", { name: /Nitrile gloves/ });
    await user.selectOptions(screen.getByLabelText("Medical supply"), "1");
    await user.type(screen.getByLabelText("Quantity"), "3");
    await user.type(screen.getByLabelText("Vendor name"), "MedLine Industries");
    await user.click(screen.getByRole("button", { name: "Record delivery" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByLabelText("Vendor name")).toHaveValue("MedLine Industries");
  });
});

describe("SupplyConsumptionForm", () => {
  it("loads current stock when a supply is selected and warns on overstock", async () => {
    const user = userEvent.setup();
    inventory.listSupplies.mockResolvedValue([gloves]);
    inventory.getSupply.mockResolvedValue(gloves);
    render(<SupplyConsumptionForm />);
    await screen.findByRole("option", { name: /Nitrile gloves/ });
    await user.selectOptions(screen.getByLabelText("Medical supply"), "1");
    expect(await screen.findByText(/Current stock:/)).toHaveTextContent("105 box");
    await user.type(screen.getByLabelText("Quantity"), "200");
    expect(screen.getByRole("alert")).toHaveTextContent("Quantity exceeds current stock");
    expect(screen.getByRole("button", { name: "Record consumption" })).toBeDisabled();
  });

  it("aborts the previous stock request when the supply changes", async () => {
    const user = userEvent.setup();
    const gauze: MedicalSupply = {
      ...gloves,
      id: 2,
      name: "Sterile gauze",
      sku: "HCR-WC-001",
      category: "wound_care",
      current_stock: 40,
    };
    inventory.listSupplies.mockResolvedValue([gloves, gauze]);
    let firstSignal: AbortSignal | undefined;
    inventory.getSupply.mockImplementation((id: number, opts?: { signal?: AbortSignal }) => {
      if (id === 1) {
        firstSignal = opts?.signal;
        return new Promise(() => {});
      }
      return Promise.resolve(gauze);
    });
    render(<SupplyConsumptionForm />);
    await screen.findByRole("option", { name: /Nitrile gloves/ });
    await user.selectOptions(screen.getByLabelText("Medical supply"), "1");
    await waitFor(() => expect(inventory.getSupply).toHaveBeenCalled());
    await user.selectOptions(screen.getByLabelText("Medical supply"), "2");
    await waitFor(() => expect(firstSignal?.aborted).toBe(true));
    expect(await screen.findByText(/Current stock:/)).toHaveTextContent("40 box");
  });

  it("shows an outbound 400 inline and refreshes stock", async () => {
    const user = userEvent.setup();
    inventory.listSupplies.mockResolvedValue([gloves]);
    inventory.getSupply.mockResolvedValue(gloves);
    inventory.createConsumption.mockImplementation(async () => {
      inventory.getSupply.mockResolvedValue({ ...gloves, current_stock: 10 });
      throw new InsufficientStockError(
        "Insufficient stock for supply 'Nitrile gloves (box of 100)'. Available: 10, requested: 11.",
      );
    });
    render(<SupplyConsumptionForm />);
    await screen.findByRole("option", { name: /Nitrile gloves/ });
    await user.selectOptions(screen.getByLabelText("Medical supply"), "1");
    await screen.findByText(/105 box/);
    await user.type(screen.getByLabelText("Quantity"), "11");
    await user.click(screen.getByRole("button", { name: "Record consumption" }));
    expect(
      await screen.findByText(/Insufficient stock for supply 'Nitrile gloves \(box of 100\)'/),
    ).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/Current stock:/)).toHaveTextContent("10 box"));
    expect(screen.getByLabelText("Quantity")).toHaveValue(11);
  });
});

describe("MovementHistory", () => {
  it("renders both movement types and has no edit or delete actions", async () => {
    const inbound: OrderMovement = {
      kind: "inbound",
      id: 1,
      supply_id: 1,
      quantity: 100,
      clinic_id: 1,
      created_at: "2026-01-01T12:00:00Z",
      user_uuid: "1",
      vendor_name: "MedLine Industries",
      consumption_type: null,
      supply: gloves,
    };
    const outbound: OrderMovement = {
      kind: "outbound",
      id: 2,
      supply_id: 1,
      quantity: 25,
      clinic_id: 1,
      created_at: "2026-01-02T12:00:00Z",
      user_uuid: "1",
      vendor_name: null,
      consumption_type: "clinical_use",
      supply: gloves,
    };
    inventory.listMovements.mockResolvedValue([inbound, outbound]);
    render(<MovementHistory />);
    expect(await screen.findByText("Delivery (inbound)")).toBeInTheDocument();
    expect(screen.getByText("Clinical use (outbound)")).toBeInTheDocument();
    expect(screen.getAllByText("Nitrile gloves (box of 100)")).toHaveLength(2);
    expect(screen.queryByRole("button", { name: /edit/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /delete/i })).not.toBeInTheDocument();
  });

  it("shows an empty state", async () => {
    inventory.listMovements.mockResolvedValue([]);
    render(<MovementHistory />);
    expect(await screen.findByText("No inventory movements have been recorded yet.")).toBeInTheDocument();
  });

  it("shows a failed load with retry", async () => {
    inventory.listMovements.mockRejectedValue(new Error("network"));
    render(<MovementHistory />);
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });
});
