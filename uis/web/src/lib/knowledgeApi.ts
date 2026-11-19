import { apiFetch, messageForStatus, parseError, readJson, ApiHttpError } from "@/lib/apiClient";

export type AgentReply = {
  answer: string;
  conversationId: string;
  memoryProposal: string | null;
};

export async function askAgent(
  question: string,
  conversationId?: string,
  signal?: AbortSignal,
): Promise<AgentReply> {
  const body: { question: string; conversation_id?: string } = { question };
  if (conversationId) body.conversation_id = conversationId;
  const response = await apiFetch("/agent/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  });
  if (!response.ok) {
    await parseError(response);
  }
  const payload = await readJson<{
    answer?: unknown;
    conversation_id?: unknown;
    memory_proposal?: { content?: unknown } | null;
  }>(response);
  if (typeof payload.answer !== "string" || !payload.answer.trim()) {
    throw new ApiHttpError(messageForStatus(500), 500);
  }
  if (typeof payload.conversation_id !== "string" || !payload.conversation_id) {
    throw new ApiHttpError(messageForStatus(500), 500);
  }
  const content = payload.memory_proposal?.content;
  return {
    answer: payload.answer,
    conversationId: payload.conversation_id,
    memoryProposal: typeof content === "string" && content.trim() ? content : null,
  };
}
