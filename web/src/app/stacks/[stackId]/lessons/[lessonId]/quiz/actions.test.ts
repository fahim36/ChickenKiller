import { afterEach, expect, it, vi } from "vitest";
import { submitLessonQuiz } from "./actions";

vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => vi.unstubAllGlobals());

it("submits the answers to the Learner's attempt and returns the API's score", async () => {
  const scored = { correct: 5, total: 6, passed: true };
  const fetch = vi.fn(async () => Response.json(scored));
  vi.stubGlobal("fetch", fetch);

  const result = await submitLessonQuiz("agentic-ai-engineer", "w01-l01", "attempt-1", {
    "w01-l01-q01": "a",
  });

  expect(result).toEqual(scored);
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/stacks/agentic-ai-engineer/lessons/w01-l01/quiz/attempt-1/answers",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ answers: { "w01-l01-q01": "a" } }),
    }),
  );
});

it("returns the grading failure instead of throwing, so the quiz can offer to resubmit", async () => {
  const detail = { code: "grading_failed", message: "Couldn't grade: submit again." };
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 503 })));

  await expect(submitLessonQuiz("s", "l", "a", {})).resolves.toEqual(detail);
});

it("fails when the API refuses the answers", async () => {
  const detail = { code: "quiz_submitted", message: "Already submitted." };
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 409 })));

  await expect(submitLessonQuiz("s", "l", "a", {})).rejects.toThrow();
});
