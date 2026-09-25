import { renderHook, waitFor } from "@testing-library/react";
import { ApiHttpError } from "@/lib/apiClient";
import { useAsyncResource } from "@/lib/useAsyncResource";

describe("useAsyncResource", () => {
  it("exposes resolved data after load", async () => {
    const loader = jest.fn().mockResolvedValue({ sku: "HCR-PPE-001" });
    const { result } = renderHook(() => useAsyncResource(loader));
    expect(result.current.loading).toBe(true);
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual({ sku: "HCR-PPE-001" });
    expect(result.current.error).toBeNull();
    expect(loader).toHaveBeenCalledTimes(1);
  });

  it("maps HTTP failures to a user message and clears data", async () => {
    const loader = jest.fn().mockRejectedValue(new ApiHttpError("nope", 500));
    const { result } = renderHook(() => useAsyncResource(loader));
    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.data).toBeNull();
    expect(result.current.error).toBe("Something went wrong on our side. Please try again.");
    expect(result.current.loading).toBe(false);
  });

  it("reload retries the loader", async () => {
    const loader = jest
      .fn()
      .mockRejectedValueOnce(new ApiHttpError("nope", 500))
      .mockResolvedValueOnce({ sku: "HCR-PPE-001" });
    const { result } = renderHook(() => useAsyncResource(loader));
    await waitFor(() => expect(result.current.error).not.toBeNull());
    await result.current.reload();
    await waitFor(() => expect(result.current.data).toEqual({ sku: "HCR-PPE-001" }));
    expect(result.current.error).toBeNull();
    expect(loader).toHaveBeenCalledTimes(2);
  });
});
