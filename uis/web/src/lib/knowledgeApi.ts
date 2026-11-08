import { apiFetch, messageForStatus, parseError, readJson, ApiHttpError } from "@/lib/apiClient";

export async function askKnowledge(question: string, signal?: AbortSignal): Promise<string> {
  const response = await apiFetch("/knowledge/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (!response.ok) {
    await parseError(response);
  }
  const payload = await readJson<{ answer?: unknown }>(response);
  if (typeof payload.answer !== "string" || !payload.answer.trim()) {
    throw new ApiHttpError(messageForStatus(500), 500);
  }
  return payload.answer;
}
