import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KnowledgeAssistant } from "@/components/KnowledgeAssistant";

jest.mock("@/lib/knowledgeApi", () => ({
  askAgent: jest.fn(),
}));

const knowledge = jest.requireMock("@/lib/knowledgeApi") as {
  askAgent: jest.Mock;
};

beforeEach(() => {
  knowledge.askAgent.mockReset();
});

function reply(answer: string, conversationId = "conv-1", memoryProposal: string | null = null) {
  return { answer, conversationId, memoryProposal };
}

describe("KnowledgeAssistant", () => {
  it("asks a question and shows the written answer", async () => {
    knowledge.askAgent.mockResolvedValue(reply("Georgia clinics do not accept Medicaid."));
    const user = userEvent.setup();
    render(<KnowledgeAssistant />);
    expect(screen.getByLabelText("Compliance question")).toBeInTheDocument();
    await user.type(
      screen.getByLabelText("Compliance question"),
      "Do Georgia clinics accept Medicaid?",
    );
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("Georgia clinics do not accept Medicaid.")).toBeInTheDocument();
    expect(knowledge.askAgent).toHaveBeenCalledTimes(1);
  });

  it("shows a loading state and ignores a second click", async () => {
    let finish: (value: ReturnType<typeof reply>) => void = () => undefined;
    knowledge.askAgent.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const user = userEvent.setup();
    render(<KnowledgeAssistant />);
    await user.type(screen.getByLabelText("Compliance question"), "What should I bring?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(screen.getByRole("status")).toHaveTextContent("Looking through the HealthCore policies");
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(knowledge.askAgent).toHaveBeenCalledTimes(1);
    finish(reply("Bring a valid ID."));
    expect(await screen.findByText("Bring a valid ID.")).toBeInTheDocument();
  });

  it("keeps the question and offers retry when the request fails", async () => {
    knowledge.askAgent.mockRejectedValueOnce(new Error("down")).mockResolvedValueOnce(reply("Try the billing team."));
    const user = userEvent.setup();
    render(<KnowledgeAssistant />);
    const box = screen.getByLabelText("Compliance question");
    await user.type(box, "Is Humana accepted?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByRole("alert")).toBeInTheDocument();
    expect(box).toHaveValue("Is Humana accepted?");
    expect(screen.queryByRole("article")).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Try the billing team.")).toBeInTheDocument();
  });

  it("does not send an empty question", async () => {
    const user = userEvent.setup();
    render(<KnowledgeAssistant />);
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a compliance question.");
    expect(knowledge.askAgent).not.toHaveBeenCalled();
  });

  it("does not send the question when Enter adds a new line", async () => {
    const user = userEvent.setup();
    render(<KnowledgeAssistant />);
    const box = screen.getByLabelText("Compliance question");
    await user.type(box, "First line{enter}Second line");
    expect(knowledge.askAgent).not.toHaveBeenCalled();
    expect(box).toHaveValue("First line\nSecond line");
  });

  it("keeps the conversation and shows a pending memory", async () => {
    knowledge.askAgent
      .mockResolvedValueOnce(reply("I cannot help with that personal task.", "conv-9"))
      .mockResolvedValueOnce(reply("Saved for later.", "conv-9", "Use the coordinator for referrals."));
    const user = userEvent.setup();
    render(<KnowledgeAssistant />);
    const box = screen.getByLabelText("Compliance question");
    await user.type(box, "Write a salary email");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("I cannot help with that personal task.")).toBeInTheDocument();
    await user.clear(box);
    await user.type(box, "What is the referral policy?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText(/Use the coordinator for referrals/)).toBeInTheDocument();
    expect(knowledge.askAgent).toHaveBeenLastCalledWith(
      "What is the referral policy?",
      "conv-9",
      expect.any(AbortSignal),
    );
  });
});