import { apiFetch } from "@/lib/apiClient";
import { uploadRfp } from "@/lib/rfp";

jest.mock("@/lib/apiClient", () => {
  const actual = jest.requireActual("@/lib/apiClient");
  return { ...actual, apiFetch: jest.fn() };
});

const api = jest.requireMock("@/lib/apiClient") as { apiFetch: jest.Mock };

describe("uploadRfp", () => {
  it("sends one PDF as multipart without a manual content type", async () => {
    api.apiFetch.mockResolvedValue({
      ok: true,
      status: 202,
      json: async () => ({ ticket_id: "t-1", status: "analyzing", processing_state: "queued" }),
    });
    const file = new File([new Uint8Array([37, 80, 68, 70])], "request.pdf", { type: "application/pdf" });
    const accepted = await uploadRfp(file);
    expect(accepted.ticket_id).toBe("t-1");
    expect(api.apiFetch).toHaveBeenCalledTimes(1);
    const [path, options] = api.apiFetch.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/rfp/tickets");
    expect(options.method).toBe("POST");
    expect(options.body).toBeInstanceOf(FormData);
    expect(options.headers).toBeUndefined();
    expect((options.body as FormData).get("file")).toBe(file);
  });

  it("returns the failed ticket from a broker 503 so the failure stays visible", async () => {
    api.apiFetch.mockResolvedValue({
      ok: false,
      status: 503,
      json: async () => ({ ticket_id: "t-503", status: "analyzing", processing_state: "failed" }),
    });
    const file = new File([new Uint8Array([37, 80, 68, 70])], "request.pdf", { type: "application/pdf" });
    await expect(uploadRfp(file)).resolves.toEqual({
      ticket_id: "t-503",
      status: "analyzing",
      processing_state: "failed",
    });
  });
});
