import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { LessonQuiz, Retakes } from "@/lib/api";
import LessonQuizPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

const quiz: LessonQuiz = {
  attempt_id: "attempt-1",
  lesson_id: "w01-l01",
  version: "v2026-09-26",
  pass_mark: 80,
  max_answer_chars: 4000,
  questions: [
    {
      id: "w01-l01-q01",
      type: "multiple_choice",
      prompt: "What does `is` compare?",
      choices: [
        { id: "a", text: "Identity" },
        { id: "b", text: "Equality" },
      ],
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function renderQuizPage() {
  const params = Promise.resolve({ stackId: "agentic-ai-engineer", lessonId: "w01-l01" });
  render(await LessonQuizPage({ params } as never));
}

it("starts (or resumes) the Lesson's quiz and shows its Questions", async () => {
  const fetch = vi.fn(async () => Response.json(quiz));
  vi.stubGlobal("fetch", fetch);

  await renderQuizPage();

  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/stacks/agentic-ai-engineer/lessons/w01-l01/quiz",
    expect.objectContaining({ method: "POST" }),
  );
  expect(screen.getByRole("group", { name: "What does is compare?" })).toBeTruthy();
  expect(screen.getByText(/Pass Mark is 80%/)).toBeTruthy();
});

it("shows the pending Retakes when the last quiz passed with Missed Questions", async () => {
  const detail = { code: "retakes_pending", message: "Finish the Retakes.", attempt_id: "attempt-1" };
  const pending: Retakes = {
    attempt_id: "attempt-1",
    lesson_id: "w01-l01",
    lesson_completed: false,
    max_answer_chars: 4000,
    retakes: [
      {
        id: "retake-1",
        missed_question_id: "w01-l01-q01",
        question: { ...quiz.questions[0], id: "w01-l01-q02", prompt: "Sibling?" },
      },
    ],
  };
  const fetch = vi.fn(async (url: string, init?: RequestInit) =>
    init?.method === "POST"
      ? Response.json({ detail }, { status: 409 })
      : Response.json(pending),
  );
  vi.stubGlobal("fetch", fetch);

  await renderQuizPage();

  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/stacks/agentic-ai-engineer/lessons/w01-l01/quiz/attempt-1/retakes",
    expect.objectContaining({ method: "GET" }),
  );
  expect(screen.getByRole("heading", { name: "Retakes", level: 1 })).toBeTruthy();
  expect(screen.getByRole("group", { name: "Sibling?" })).toBeTruthy();
});

it("explains why when the quiz can't be started", async () => {
  const detail = {
    code: "lesson_locked",
    message: "This Lesson is locked. Complete the Lessons before it first.",
  };
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 409 })));

  await renderQuizPage();

  expect(screen.getByRole("alert").textContent).toBe(detail.message);
  expect(screen.getByRole("link", { name: "Back to the Lesson" }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer/lessons/w01-l01",
  );
  expect(screen.queryByRole("group")).toBeNull();
});
