import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { LessonQuiz as Quiz, LessonQuizResult, QuizAnswers } from "@/lib/api";
import { LessonQuiz } from "./LessonQuiz";

const quiz: Quiz = {
  attempt_id: "3f1c7a52-0000-4000-8000-000000000001",
  lesson_id: "w01-l01",
  version: "v2026-09-26",
  pass_mark: 80,
  questions: [1, 2, 3, 4, 5, 6].map((n) => ({
    id: `w01-l01-q0${n}`,
    type: "multiple_choice",
    prompt: `Question ${n}?`,
    choices: [
      { id: "a", text: `Right ${n}` },
      { id: "b", text: `Wrong ${n}` },
    ],
  })),
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
    questions: quiz.questions.map((q, i) => ({ id: q.id, correct: i < correct })),
  };
}

afterEach(cleanup);

function renderQuiz(submitAction: (answers: QuizAnswers) => Promise<LessonQuizResult>) {
  render(<LessonQuiz quiz={quiz} stackId="agentic-ai-engineer" submitAction={submitAction} />);
}

function choose(n: number, text: string) {
  const question = screen.getByRole("group", { name: new RegExp(`Question ${n}\\?`) });
  fireEvent.click(within(question).getByRole("radio", { name: text }));
}

const submitButton = () => screen.getByRole("button", { name: "Submit answers" });

it("shows the six Questions with their choices", () => {
  renderQuiz(vi.fn());

  expect(screen.getAllByRole("group")).toHaveLength(6);
  const first = screen.getByRole("group", { name: /Question 1\?/ });
  expect(within(first).getAllByRole("radio").map((r) => r.getAttribute("value"))).toEqual([
    "a",
    "b",
  ]);
  expect(within(first).getByText("Right 1")).toBeTruthy();
});

it("submits the chosen answers, leaving unanswered Questions out", async () => {
  const submitAction = vi.fn(async () => result(5));
  renderQuiz(submitAction);

  choose(1, "Right 1");
  choose(2, "Wrong 2");
  choose(2, "Right 2");
  fireEvent.click(submitButton());

  await vi.waitFor(() =>
    expect(submitAction).toHaveBeenCalledWith({ "w01-l01-q01": "a", "w01-l01-q02": "a" }),
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

  const marks = quiz.questions.map((_, i) =>
    within(screen.getByRole("group", { name: new RegExp(`Question ${i + 1}\\?`) })).getByText(
      /^(Correct|Missed)$/,
    ).textContent,
  );
  expect(marks).toEqual(["Correct", "Correct", "Correct", "Correct", "Missed", "Missed"]);
});

it("says so and lets the Learner try again when submitting fails", async () => {
  const submitAction = vi
    .fn<(answers: QuizAnswers) => Promise<LessonQuizResult>>()
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
