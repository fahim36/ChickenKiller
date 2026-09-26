import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type {
  AnsweredQuestion,
  GradingFailed,
  QuizQuestion,
  ReviewAnswerResult,
  ReviewRound,
} from "@/lib/api";
import { ReviewRoundFlow } from "./ReviewRoundFlow";

afterEach(cleanup);

const mc: QuizQuestion = {
  id: "w01-l01-q01",
  type: "multiple_choice",
  prompt: "What does `is` compare?",
  choices: [
    { id: "a", text: "Identity" },
    { id: "b", text: "Equality" },
  ],
};

const written: QuizQuestion = {
  id: "w01-l01-q07",
  type: "written",
  prompt: "Explain the GIL.",
  choices: [],
};

const round: ReviewRound = {
  id: "round-1",
  number: 1,
  state: "optional",
  opened_at: "2026-09-26T04:00:00Z",
  pending_at: "2026-09-26T06:00:00Z",
  finished_at: null,
  answered: 0,
  total: 2,
  max_answer_chars: 4000,
  remaining: [mc, written],
  results: [],
};

function answered(question: QuizQuestion, response: string): AnsweredQuestion {
  const isWritten = question.type === "written";
  return {
    ...question,
    response,
    feedback: isWritten ? "Missing: one lock per interpreter." : null,
    answer: isWritten ? null : "a",
    model_answer: isWritten
      ? { summary: "One thread runs Python bytecode at a time.", key_points: ["One lock"] }
      : null,
    explanation: `Because of ${question.id}.`,
    materials: [],
  };
}

function result(
  question: QuizQuestion,
  response: string,
  correct: boolean,
  answeredCount: number,
): ReviewAnswerResult {
  return {
    correct,
    question: answered(question, response),
    round: {
      ...round,
      answered: answeredCount,
      state: answeredCount === round.total ? "finished" : "optional",
      finished_at: answeredCount === round.total ? "2026-09-26T04:10:00Z" : null,
    },
  };
}

type Answer = (
  questionId: string,
  answer: string | null,
) => Promise<ReviewAnswerResult | GradingFailed>;

function renderFlow(answerAction: Answer) {
  render(
    <ReviewRoundFlow round={round} stackId="agentic-ai-engineer" answerAction={answerAction} />,
  );
}

function submit() {
  fireEvent.click(screen.getByRole("button", { name: "Submit answer" }));
}

it("asks the round's Questions one at a time, in order", () => {
  renderFlow(vi.fn());

  expect(screen.getByText("Question 1 of 2")).toBeTruthy();
  expect(screen.getByRole("group", { name: "What does is compare?" })).toBeTruthy();
  expect(screen.queryByText("Explain the GIL.")).toBeNull();
});

it("sends the answer to that Question and moves on after a right one", async () => {
  const answerAction = vi.fn(async () => result(mc, "a", true, 1));
  renderFlow(answerAction);

  fireEvent.click(screen.getByRole("radio", { name: "Identity" }));
  submit();

  expect(await screen.findByText("Correct")).toBeTruthy();
  expect(answerAction).toHaveBeenCalledWith("w01-l01-q01", "a");
  expect(screen.queryByText("Because of w01-l01-q01.")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Next Question" }));
  expect(screen.getByText("Question 2 of 2")).toBeTruthy();
  expect(screen.getByLabelText("Your answer")).toBeTruthy();
});

it("shows the Explanation and the correct answer after a wrong answer", async () => {
  renderFlow(vi.fn(async () => result(mc, "b", false, 1)));

  fireEvent.click(screen.getByRole("radio", { name: "Equality" }));
  submit();

  expect(await screen.findByText("Not quite. Read the Explanation before moving on.")).toBeTruthy();
  expect(screen.getByText("Because of w01-l01-q01.")).toBeTruthy();
  expect(screen.getByText("Identity")).toBeTruthy(); // the correct answer
});

it("shows the Model Answer and the grader's feedback after a missed written answer", async () => {
  const answerAction = vi
    .fn<Answer>()
    .mockResolvedValueOnce(result(mc, "a", true, 1))
    .mockResolvedValueOnce(result(written, "No idea.", false, 2));
  renderFlow(answerAction);
  fireEvent.click(screen.getByRole("radio", { name: "Identity" }));
  submit();
  fireEvent.click(await screen.findByRole("button", { name: "Next Question" }));

  fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "No idea." } });
  submit();

  expect(await screen.findByText("Missing: one lock per interpreter.")).toBeTruthy();
  expect(screen.getByText("One thread runs Python bytecode at a time.")).toBeTruthy();
  expect(screen.getByText("Because of w01-l01-q07.")).toBeTruthy();
  expect(answerAction).toHaveBeenLastCalledWith("w01-l01-q07", "No idea.");
});

it("says the round is finished after its last answer", async () => {
  const answerAction = vi
    .fn<Answer>()
    .mockResolvedValueOnce(result(mc, "a", true, 1))
    .mockResolvedValueOnce(result(written, "The right answer.", true, 2));
  renderFlow(answerAction);
  fireEvent.click(screen.getByRole("radio", { name: "Identity" }));
  submit();
  fireEvent.click(await screen.findByRole("button", { name: "Next Question" }));
  fireEvent.change(screen.getByLabelText("Your answer"), {
    target: { value: "The right answer." },
  });
  submit();

  fireEvent.click(await screen.findByRole("button", { name: "Finish" }));

  expect(screen.getByRole("status").textContent).toContain("Review Round 1 is done: 2 of 2 right.");
  expect(screen.getByRole("link", { name: "Back to the Week map" }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer",
  );
});

it("lets the Learner answer again when grading fails, with nothing counted", async () => {
  const failure: GradingFailed = { code: "grading_failed", message: "Couldn't grade: again." };
  const answerAction = vi.fn<Answer>().mockResolvedValueOnce(failure);
  render(
    <ReviewRoundFlow
      round={{ ...round, remaining: [written] }}
      stackId="agentic-ai-engineer"
      answerAction={answerAction}
    />,
  );
  fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "My answer." } });

  submit();

  expect((await screen.findByRole("alert")).textContent).toBe("Couldn't grade: again.");
  expect((screen.getByLabelText("Your answer") as HTMLTextAreaElement).value).toBe("My answer.");
  expect(screen.getByRole("button", { name: "Submit again" })).toBeTruthy();
});
