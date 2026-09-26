import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type {
  AnsweredQuestion,
  GradingFailed,
  QuizQuestion,
  Retake,
  RetakeResult,
} from "@/lib/api";
import { RetakeFlow } from "./RetakeFlow";

afterEach(cleanup);

function question(n: number): QuizQuestion {
  return {
    id: `w01-l01-q0${n}`,
    type: "multiple_choice",
    prompt: `Sibling ${n}?`,
    choices: [
      { id: "a", text: `Right ${n}` },
      { id: "b", text: `Wrong ${n}` },
    ],
  };
}

const retake: Retake = { id: "retake-1", missed_question_id: "w01-l01-q01", question: question(2) };

function answered(n: number, response: string): AnsweredQuestion {
  return {
    ...question(n),
    response,
    feedback: null,
    answer: "a",
    model_answer: null,
    explanation: `Because of sibling ${n}.`,
    materials: [],
  };
}

function wrong(n: number, next: number): RetakeResult {
  return {
    retake_id: retake.id,
    correct: false,
    question: answered(n, "b"),
    next_question: question(next),
    pending: 1,
    lesson_completed: false,
  };
}

function right(n: number): RetakeResult {
  return {
    retake_id: retake.id,
    correct: true,
    question: answered(n, "a"),
    next_question: null,
    pending: 0,
    lesson_completed: true,
  };
}

type Answer = (retakeId: string, answer: string | null) => Promise<RetakeResult | GradingFailed>;

function renderFlow(answerAction: Answer, retakes: Retake[] = [retake]) {
  render(
    <RetakeFlow
      retakes={retakes}
      stackId="agentic-ai-engineer"
      maxAnswerChars={4000}
      answerAction={answerAction}
    />,
  );
}

function choose(text: string) {
  fireEvent.click(screen.getByRole("radio", { name: text }));
  fireEvent.click(screen.getByRole("button", { name: "Submit Retake" }));
}

it("asks the sibling Question for each pending Retake", () => {
  renderFlow(vi.fn());

  const group = screen.getByRole("group", { name: "Sibling 2?" });
  expect(within(group).getAllByRole("radio").map((r) => r.getAttribute("value"))).toEqual([
    "a",
    "b",
  ]);
});

it("submits the chosen answer to the Retake", async () => {
  const answerAction = vi.fn<Answer>(async () => right(2));
  renderFlow(answerAction);

  choose("Right 2");

  await vi.waitFor(() => expect(answerAction).toHaveBeenCalledWith("retake-1", "a"));
});

it("after a wrong Retake shows its Explanation and offers another sibling", async () => {
  renderFlow(vi.fn<Answer>(async () => wrong(2, 3)));

  choose("Wrong 2");

  const explained = await screen.findByRole("article", { name: "Sibling 2?" });
  expect(within(explained).getByText("Because of sibling 2.")).toBeTruthy();
  expect(screen.getByRole("group", { name: "Sibling 3?" })).toBeTruthy();
  expect(screen.queryByRole("group", { name: "Sibling 2?" })).toBeNull();
  expect(screen.queryByRole("status")).toBeNull();
});

it("says the Lesson is Completed once every Retake is correct", async () => {
  const answerAction = vi
    .fn<Answer>()
    .mockResolvedValueOnce(wrong(2, 3))
    .mockResolvedValueOnce(right(3));
  renderFlow(answerAction);

  choose("Wrong 2");
  await screen.findByRole("group", { name: "Sibling 3?" });
  choose("Right 3");

  const status = await screen.findByRole("status");
  expect(status.textContent).toContain("this Lesson is Completed and the next one is Unlocked");
  expect(
    within(status).getByRole("link", { name: "Back to the Week map" }).getAttribute("href"),
  ).toBe("/stacks/agentic-ai-engineer");
  expect(screen.queryByRole("group")).toBeNull();
});

it("keeps the other Retakes pending until they are correct too", async () => {
  const second: Retake = { id: "retake-2", missed_question_id: "w01-l01-q05", question: question(6) };
  renderFlow(
    vi.fn<Answer>(async () => ({ ...right(2), pending: 1, lesson_completed: false })),
    [retake, second],
  );

  fireEvent.click(screen.getByRole("radio", { name: "Right 2" }));
  fireEvent.click(
    within(screen.getByRole("group", { name: "Sibling 2?" }).closest("form")!).getByRole(
      "button",
      { name: "Submit Retake" },
    ),
  );

  expect(await screen.findByText("Correct")).toBeTruthy();
  expect(screen.queryByRole("group", { name: "Sibling 2?" })).toBeNull();
  expect(screen.getByRole("group", { name: "Sibling 6?" })).toBeTruthy();
  expect(screen.queryByRole("status")).toBeNull();
});

it("says so and lets the Learner try again when submitting fails", async () => {
  const answerAction = vi
    .fn<Answer>()
    .mockRejectedValueOnce(new Error("HTTP 500"))
    .mockResolvedValueOnce(right(2));
  renderFlow(answerAction);

  choose("Right 2");
  expect((await screen.findByRole("alert")).textContent).toBe(
    "Couldn't submit your Retake. Try again.",
  );
  fireEvent.click(screen.getByRole("button", { name: "Submit Retake" }));

  expect(await screen.findByRole("status")).toBeTruthy();
});

const writtenSibling: QuizQuestion = {
  id: "w01-l01-q08",
  type: "written",
  prompt: "Explain sibling 8.",
  choices: [],
};
const writtenRetake: Retake = {
  id: "retake-w",
  missed_question_id: "w01-l01-q07",
  question: writtenSibling,
};

function writeAnswer(text: string) {
  const box = within(screen.getByRole("group", { name: "Explain sibling 8." })).getByRole(
    "textbox",
    { name: "Your answer" },
  );
  fireEvent.change(box, { target: { value: text } });
  return box as HTMLTextAreaElement;
}

it("answers a written sibling in a text box", async () => {
  const answerAction = vi.fn<Answer>(async () => ({ ...right(8), retake_id: "retake-w" }));
  renderFlow(answerAction, [writtenRetake]);

  expect(writeAnswer("The right idea.").getAttribute("maxlength")).toBe("4000");
  fireEvent.click(screen.getByRole("button", { name: "Submit Retake" }));

  await vi.waitFor(() => expect(answerAction).toHaveBeenCalledWith("retake-w", "The right idea."));
  expect(await screen.findByRole("status")).toBeTruthy();
});

it("after a wrong written Retake shows the grader's feedback and the Model Answer", async () => {
  const graded: RetakeResult = {
    retake_id: "retake-w",
    correct: false,
    question: {
      ...writtenSibling,
      response: "No idea.",
      feedback: "Missing: the loop.",
      answer: null,
      model_answer: { summary: "Agents loop.", key_points: ["loop", "tools"] },
      explanation: "Because of sibling 8.",
      materials: [],
    },
    next_question: writtenSibling,
    pending: 1,
    lesson_completed: false,
  };
  renderFlow(vi.fn<Answer>(async () => graded), [writtenRetake]);

  writeAnswer("No idea.");
  fireEvent.click(screen.getByRole("button", { name: "Submit Retake" }));

  const explained = await screen.findByRole("article", { name: "Explain sibling 8." });
  expect(within(explained).getByText("Missing: the loop.")).toBeTruthy();
  expect(within(explained).getByText("Agents loop.")).toBeTruthy();
  // The same sibling is asked again, with an empty box.
  expect(writeAnswer("").value).toBe("");
});

it("says nothing was counted when grading a Retake fails, and lets the Learner submit again", async () => {
  const failure: GradingFailed = { code: "grading_failed", message: "Couldn't grade: nothing counted." };
  const answerAction = vi
    .fn<Answer>()
    .mockResolvedValueOnce(failure)
    .mockResolvedValueOnce({ ...right(8), retake_id: "retake-w" });
  renderFlow(answerAction, [writtenRetake]);

  writeAnswer("The right idea.");
  fireEvent.click(screen.getByRole("button", { name: "Submit Retake" }));

  expect((await screen.findByRole("alert")).textContent).toBe(failure.message);
  expect(writeAnswer("The right idea.").value).toBe("The right idea.");
  fireEvent.click(screen.getByRole("button", { name: "Submit again" }));

  expect(await screen.findByRole("status")).toBeTruthy();
  expect(answerAction).toHaveBeenLastCalledWith("retake-w", "The right idea.");
});
