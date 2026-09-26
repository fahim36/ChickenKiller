import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { GradingFailed, LessonQuiz as Quiz, LessonQuizResult, QuizAnswers } from "@/lib/api";
import { LessonQuiz } from "./LessonQuiz";

// Four multiple-choice Questions (1 to 4), then two written ones (5 and 6).
const quiz: Quiz = {
  attempt_id: "3f1c7a52-0000-4000-8000-000000000001",
  lesson_id: "w01-l01",
  version: "v2026-09-26",
  pass_mark: 80,
  max_answer_chars: 4000,
  questions: [
    ...[1, 2, 3, 4].map((n) => ({
      id: `w01-l01-q0${n}`,
      type: "multiple_choice" as const,
      prompt: `Question ${n}?`,
      choices: [
        { id: "a", text: `Right ${n}` },
        { id: "b", text: `Wrong ${n}` },
      ],
    })),
    ...[5, 6].map((n) => ({
      id: `w01-l01-q0${n}`,
      type: "written" as const,
      prompt: `Question ${n}?`,
      choices: [],
    })),
  ],
};

function result(correct: number): LessonQuizResult {
  return {
    attempt_id: quiz.attempt_id,
    lesson_id: "w01-l01",
    correct,
    total: 6,
    percent: Math.round((correct / 6) * 100),
    passed: correct >= 5,
    pass_mark: 80,
    questions: quiz.questions.map((q, i) => ({ id: q.id, correct: i < correct, feedback: null })),
  };
}

afterEach(cleanup);

type Submit = (answers: QuizAnswers) => Promise<LessonQuizResult | GradingFailed>;

function renderQuiz(submitAction: Submit) {
  render(<LessonQuiz quiz={quiz} stackId="agentic-ai-engineer" submitAction={submitAction} />);
}

const question = (n: number) => screen.getByRole("group", { name: new RegExp(`Question ${n}\\?`) });

function choose(n: number, text: string) {
  fireEvent.click(within(question(n)).getByRole("radio", { name: text }));
}

function write(n: number, text: string) {
  fireEvent.change(within(question(n)).getByRole("textbox", { name: "Your answer" }), {
    target: { value: text },
  });
}

const submitButton = () => screen.getByRole("button", { name: /Submit/ });

it("shows the multiple-choice Questions with their choices and the written ones with a box", () => {
  renderQuiz(vi.fn());

  expect(screen.getAllByRole("group")).toHaveLength(6);
  const first = question(1);
  expect(within(first).getAllByRole("radio").map((r) => r.getAttribute("value"))).toEqual([
    "a",
    "b",
  ]);
  expect(within(first).getByText("Right 1")).toBeTruthy();
  expect(within(question(5)).queryAllByRole("radio")).toHaveLength(0);
  const box = within(question(5)).getByRole("textbox", { name: "Your answer" });
  expect(box.getAttribute("maxlength")).toBe("4000");
});

it("submits the chosen and written answers, leaving unanswered Questions out", async () => {
  const submitAction = vi.fn(async () => result(5));
  renderQuiz(submitAction);

  choose(1, "Right 1");
  choose(2, "Wrong 2");
  choose(2, "Right 2");
  write(5, "An agent calls tools in a loop.");
  write(6, "   ");
  fireEvent.click(submitButton());

  await vi.waitFor(() =>
    expect(submitAction).toHaveBeenCalledWith({
      "w01-l01-q01": "a",
      "w01-l01-q02": "a",
      "w01-l01-q05": "An agent calls tools in a loop.",
    }),
  );
});

it("shows a pass with the score and a way back to the Week map", async () => {
  renderQuiz(vi.fn(async () => result(5)));

  fireEvent.click(submitButton());

  const status = await screen.findByRole("status");
  expect(status.textContent).toContain("5 of 6 (83%)");
  expect(status.textContent).toContain("Passed");
  expect(
    screen.getByRole("link", { name: "Back to the Week map" }).getAttribute("href"),
  ).toBe("/stacks/agentic-ai-engineer");
  expect(submitButton().hasAttribute("disabled")).toBe(true);
});

it("shows a fail against the Pass Mark and offers a fresh quiz", async () => {
  renderQuiz(vi.fn(async () => result(4)));

  fireEvent.click(submitButton());

  const status = await screen.findByRole("status");
  expect(status.textContent).toContain("4 of 6 (67%)");
  expect(status.textContent).toContain("Not passed: the Pass Mark is 80%");
  expect(
    screen.getByRole("link", { name: "Take a fresh Lesson Quiz" }).getAttribute("href"),
  ).toBe("/stacks/agentic-ai-engineer/lessons/w01-l01/quiz");
});

it("marks which Questions were right and which were missed", async () => {
  renderQuiz(vi.fn(async () => result(4)));

  fireEvent.click(submitButton());
  await screen.findByRole("status");

  const marks = quiz.questions.map(
    (_, i) => within(question(i + 1)).getByText(/^(Correct|Missed)$/).textContent,
  );
  expect(marks).toEqual(["Correct", "Correct", "Correct", "Correct", "Missed", "Missed"]);
});

it("shows the grader's feedback on each written answer", async () => {
  const graded = result(5);
  graded.questions[4].feedback = "Covers every key point.";
  graded.questions[5].feedback = "Missing: the loop.";
  renderQuiz(vi.fn(async () => graded));

  fireEvent.click(submitButton());
  await screen.findByRole("status");

  expect(within(question(5)).getByText("Correct")).toBeTruthy();
  expect(within(question(5)).getByText("Covers every key point.")).toBeTruthy();
  expect(within(question(6)).getByText("Missed")).toBeTruthy();
  expect(within(question(6)).getByText("Missing: the loop.")).toBeTruthy();
});

it("says nothing was counted when grading fails, and lets the Learner submit again", async () => {
  const failure: GradingFailed = {
    code: "grading_failed",
    message: "Your written answers couldn't be graded just now. Nothing was counted.",
  };
  const submitAction = vi.fn<Submit>().mockResolvedValueOnce(failure).mockResolvedValueOnce(result(6));
  renderQuiz(submitAction);
  write(5, "My answer.");

  fireEvent.click(submitButton());

  expect((await screen.findByRole("alert")).textContent).toBe(failure.message);
  expect(screen.queryByRole("status")).toBeNull();
  expect(submitButton().textContent).toBe("Submit again");
  const box = within(question(5)).getByRole("textbox", { name: "Your answer" });
  expect((box as HTMLTextAreaElement).value).toBe("My answer.");

  fireEvent.click(submitButton());

  expect((await screen.findByRole("status")).textContent).toContain("6 of 6 (100%)");
  expect(submitAction).toHaveBeenLastCalledWith({ "w01-l01-q05": "My answer." });
  expect(screen.queryByRole("alert")).toBeNull();
});

it("says so and lets the Learner try again when submitting fails", async () => {
  const submitAction = vi
    .fn<Submit>()
    .mockRejectedValueOnce(new Error("HTTP 500"))
    .mockResolvedValueOnce(result(6));
  renderQuiz(submitAction);

  fireEvent.click(submitButton());

  expect((await screen.findByRole("alert")).textContent).toBe(
    "Couldn't submit your answers. Try again.",
  );
  fireEvent.click(submitButton());
  expect((await screen.findByRole("status")).textContent).toContain("6 of 6 (100%)");
});
