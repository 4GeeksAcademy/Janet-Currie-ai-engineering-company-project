import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { KnowledgeAssistant } from "@/components/KnowledgeAssistant";

jest.mock("@/lib/knowledgeApi", () => ({
  askKnowledge: jest.fn(),
}));

const knowledge = jest.requireMock("@/lib/knowledgeApi") as {
  askKnowledge: jest.Mock;
};

beforeEach(() => {
  knowledge.askKnowledge.mockReset();
});

describe("KnowledgeAssistant", () => {
  it("asks a question and shows the written answer", async () => {
    knowledge.askKnowledge.mockResolvedValue("Georgia clinics do not accept Medicaid.");
    const user = userEvent.setup();
    render(<KnowledgeAssistant />);
    expect(screen.getByLabelText("Policy or procedure question")).toBeInTheDocument();
    await user.type(
      screen.getByLabelText("Policy or procedure question"),
      "Do Georgia clinics accept Medicaid?",
    );
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(await screen.findByText("Georgia clinics do not accept Medicaid.")).toBeInTheDocument();
    expect(knowledge.askKnowledge).toHaveBeenCalledTimes(1);
  });

  it("shows a loading state and ignores a second click", async () => {
    let finish: (value: string) => void = () => undefined;
    knowledge.askKnowledge.mockImplementation(
      () =>
        new Promise<string>((resolve) => {
          finish = resolve;
        }),
    );
    const user = userEvent.setup();
    render(<KnowledgeAssistant />);
    await user.type(screen.getByLabelText("Policy or procedure question"), "What should I bring?");
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(screen.getByRole("status")).toHaveTextContent("Looking through the HealthCore policies");
    expect(screen.getByRole("button", { name: "Ask" })).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Ask" }));
    expect(knowledge.askKnowledge).toHaveBeenCalledTimes(1);
    finish("Bring a valid ID.");
    expect(await screen.findByText("Bring a valid ID.")).toBeInTheDocument();
  });

  it("keeps the question and offers retry when the request fails", async () => {
    knowledge.askKnowledge.mockRejectedValueOnce(new Error("down")).mockResolvedValueOnce("Try the billing team.");
    const user = userEvent.setup();
    render(<KnowledgeAssistant />);
    const box = screen.getByLabelText("Policy or procedure question");
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
    expect(screen.getByRole("alert")).toHaveTextContent("Enter a policy or procedure question.");
    expect(knowledge.askKnowledge).not.toHaveBeenCalled();
  });

  it("does not send the question when Enter adds a new line", async () => {
    const user = userEvent.setup();
    render(<KnowledgeAssistant />);
    const box = screen.getByLabelText("Policy or procedure question");
    await user.type(box, "First line{enter}Second line");
    expect(knowledge.askKnowledge).not.toHaveBeenCalled();
    expect(box).toHaveValue("First line\nSecond line");
  });
});