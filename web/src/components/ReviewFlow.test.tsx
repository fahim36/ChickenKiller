import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type {
  AnsweredQuestion,
  GradingFailed,
  ReviewAnswerResult,
  ReviewQuestion,
  ReviewSet,
} from "@/lib/api";
import { ReviewFlow } from "./ReviewFlow";

afterEach(cleanup);

const mc: ReviewQuestion = {
  stack_id: "agentic-ai-engineer",
  stack_name: "Agentic AI Engineer",
  id: "w01-l01-q01",
  type: "multiple_choice",
  prompt: "What does `is` compare?",
  choices: [
    { id: "a", text: "Identity" },
    { id: "b", text: "Equality" },
  ],
};

const written: ReviewQuestion = {
  stack_id: "data-engineer",
  stack_name: "Data Engineer",
  id: "w01-l01-q07",
  type: "written",
  prompt: "Explain the GIL.",
  choices: [],
};

const set: ReviewSet = { size: 10, max_answer_chars: 4000, questions: [mc, written] };

function answered(question: ReviewQuestion, response: string): AnsweredQuestion {
  const isWritten = question.type === "written";
  return {
    id: question.id,
    type: question.type,
    prompt: question.prompt,
    choices: question.choices,
    response,
    selected: [],
    feedback: isWritten ? "Missing: one lock per interpreter." : null,
    answer: isWritten ? null : "a",
    answers: [],
    model_answer: isWritten
      ? { summary: "One thread runs Python bytecode at a time.", key_points: ["One lock"] }
      : null,
    explanation: `Because of ${question.id}.`,
    materials: [],
    sources: [
      {
        url: "https://docs.python.org/3/reference/expressions.html#is",
        title: "Identity comparisons",
        publisher: "Python Software Foundation",
        accessed: "2026-09-20",
        claim: "`is` tests object identity.",
      },
    ],
  };
}

function result(question: ReviewQuestion, response: string, correct: boolean): ReviewAnswerResult {
  return { correct, question: answered(question, response) };
}

type Answer = (
  stackId: string,
  questionId: string,
  answer: string | string[] | null,
) => Promise<ReviewAnswerResult | GradingFailed>;

function renderFlow(answerAction: Answer, reviewSet: ReviewSet = set) {
  render(<ReviewFlow reviewSet={reviewSet} answerAction={answerAction} />);
}

function submit() {
  fireEvent.click(screen.getByRole("button", { name: "Submit answer" }));
}

async function answerFirstRight() {
  fireEvent.click(screen.getByRole("radio", { name: "Identity" }));
  submit();
  fireEvent.click(await screen.findByRole("button", { name: "Next Question" }));
}

it("asks the set's Questions one at a time, in order, with each one's Stack", () => {
  renderFlow(vi.fn());

  expect(screen.getByText("Agentic AI Engineer · Question 1 of 2")).toBeTruthy();
  expect(screen.getByRole("group", { name: "What does is compare?" })).toBeTruthy();
  expect(screen.queryByText("Explain the GIL.")).toBeNull();
});

it("sends the answer to that Question on its Stack and moves on after a right one", async () => {
  const answerAction = vi.fn(async () => result(mc, "a", true));
  renderFlow(answerAction);

  fireEvent.click(screen.getByRole("radio", { name: "Identity" }));
  submit();

  expect(await screen.findByText("Correct")).toBeTruthy();
  expect(answerAction).toHaveBeenCalledWith("agentic-ai-engineer", "w01-l01-q01", "a");
  expect(screen.queryByText("Because of w01-l01-q01.")).toBeNull();
  fireEvent.click(screen.getByRole("button", { name: "Next Question" }));
  expect(screen.getByText("Data Engineer · Question 2 of 2")).toBeTruthy();
  expect(screen.getByLabelText("Your answer")).toBeTruthy();
});

it("shows the Explanation and the correct answer after a wrong answer", async () => {
  renderFlow(vi.fn(async () => result(mc, "b", false)));

  fireEvent.click(screen.getByRole("radio", { name: "Equality" }));
  submit();

  expect(await screen.findByText("Not quite. Read the Explanation before moving on.")).toBeTruthy();
  expect(screen.getByText("Because of w01-l01-q01.")).toBeTruthy();
  expect(screen.getByText("Identity")).toBeTruthy(); // the correct answer
});

it("shows every Source after the Explanation of a wrong answer", async () => {
  renderFlow(vi.fn(async () => result(mc, "b", false)));

  fireEvent.click(screen.getByRole("radio", { name: "Equality" }));
  submit();

  const sources = await screen.findByRole("list", { name: "Sources" });
  expect(sources.textContent).toBe(
    "Identity comparisons · Python Software Foundation: is tests object identity.",
  );
  expect(screen.getByRole("link", { name: "Identity comparisons" }).getAttribute("href")).toBe(
    "https://docs.python.org/3/reference/expressions.html#is",
  );
});

it("shows the Model Answer and the grader's feedback after a missed written answer", async () => {
  const answerAction = vi
    .fn<Answer>()
    .mockResolvedValueOnce(result(mc, "a", true))
    .mockResolvedValueOnce(result(written, "No idea.", false));
  renderFlow(answerAction);
  await answerFirstRight();

  fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "No idea." } });
  submit();

  expect(await screen.findByText("Missing: one lock per interpreter.")).toBeTruthy();
  expect(screen.getByText("One thread runs Python bytecode at a time.")).toBeTruthy();
  expect(screen.getByText("Because of w01-l01-q07.")).toBeTruthy();
  expect(answerAction).toHaveBeenLastCalledWith("data-engineer", "w01-l01-q07", "No idea.");
});

it("says the set is done after its last answer and offers the next set", async () => {
  const answerAction = vi
    .fn<Answer>()
    .mockResolvedValueOnce(result(mc, "a", true))
    .mockResolvedValueOnce(result(written, "No idea.", false));
  renderFlow(answerAction);
  await answerFirstRight();
  fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "No idea." } });
  submit();

  fireEvent.click(await screen.findByRole("button", { name: "Finish" }));

  expect(screen.getByRole("status").textContent).toContain("Set done: 1 of 2 right.");
  expect(screen.getByRole("link", { name: "Next set" }).getAttribute("href")).toBe("/review");
});

it("lets the Learner skip a Question without answering it", () => {
  const answerAction = vi.fn<Answer>();
  renderFlow(answerAction);

  fireEvent.click(screen.getByRole("button", { name: "Skip" }));

  expect(screen.getByText("Data Engineer · Question 2 of 2")).toBeTruthy();
  expect(answerAction).not.toHaveBeenCalled();
});

it("lets the Learner answer again when grading fails, with nothing counted", async () => {
  const failure: GradingFailed = { code: "grading_failed", message: "Couldn't grade: again." };
  const answerAction = vi.fn<Answer>().mockResolvedValueOnce(failure);
  renderFlow(answerAction, { ...set, questions: [written] });
  fireEvent.change(screen.getByLabelText("Your answer"), { target: { value: "My answer." } });

  submit();

  expect((await screen.findByRole("alert")).textContent).toBe("Couldn't grade: again.");
  expect((screen.getByLabelText("Your answer") as HTMLTextAreaElement).value).toBe("My answer.");
  expect(screen.getByRole("button", { name: "Submit again" })).toBeTruthy();
});
