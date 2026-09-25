import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import OperationsPage from "@/app/(protected)/operations/page";
import IncidentsPage from "@/app/(protected)/incidents/page";

jest.mock("next/dynamic", () => {
  return (loader: () => Promise<unknown>, options?: { loading?: () => ReactNode }) => {
    const Loading = options?.loading;
    function DynamicStub() {
      return Loading ? Loading() : null;
    }
    return DynamicStub;
  };
});

describe("lazy staff pages", () => {
  it("operations shows an accessible loading state before the analytics island", () => {
    render(<OperationsPage />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading operations analytics…");
  });

  it("incidents shows an accessible loading state before the analyzer island", () => {
    render(<IncidentsPage />);
    expect(screen.getByRole("status")).toHaveTextContent("Loading incident analyzer…");
  });
});
