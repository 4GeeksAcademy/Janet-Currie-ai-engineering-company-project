import type { MedicalSupply } from "@/lib/inventory";

type SupplySelectProps = {
  id?: string;
  label?: string;
  supplies: MedicalSupply[];
  value: string;
  onChange: (supplyId: string) => void;
  disabled?: boolean;
};

export function SupplySelect({
  id = "supply_id",
  label = "Medical supply",
  supplies,
  value,
  onChange,
  disabled,
}: SupplySelectProps) {
  return (
    <label className="block text-sm text-slate-700" htmlFor={id}>
      {label}
      <select
        id={id}
        className="mt-1 w-full rounded-md border border-slate-300 px-2 py-2"
        value={value}
        disabled={disabled}
        onChange={(event) => onChange(event.target.value)}
        required
      >
        <option value="">Select a medical supply</option>
        {supplies.map((supply) => (
          <option key={supply.id} value={String(supply.id)}>
            {supply.name} ({supply.sku})
          </option>
        ))}
      </select>
    </label>
  );
}
