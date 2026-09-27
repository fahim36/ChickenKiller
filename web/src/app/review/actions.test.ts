import { afterEach, expect, it, vi } from "vitest";
import { answerReviewQuestion } from "./actions";

vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => vi.unstubAllGlobals());

it("sends the answer to that Question on its Stack and returns the API's result", async () => {
  const marked = { correct: false, question: { id: "w01-l01-q01" } };
  const fetch = vi.fn(async () => Response.json(marked));
  vi.stubGlobal("fetch", fetch);

  const result = await answerReviewQuestion("agentic-ai-engineer", "w01-l01-q01", "b");

  expect(result).toEqual(marked);
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/review/answers",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ stack_id: "agentic-ai-engineer", question_id: "w01-l01-q01", answer: "b" }),
    }),
  );
});

it("returns the grading failure instead of throwing, so the Learner can resubmit", async () => {
  const detail = { code: "grading_failed", message: "Couldn't grade: submit again." };
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 503 })));

  await expect(answerReviewQuestion("s", "q", "An answer.")).resolves.toEqual(detail);
});
