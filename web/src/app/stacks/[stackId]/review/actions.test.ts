import { afterEach, expect, it, vi } from "vitest";
import { answerReviewQuestion } from "./actions";

vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => vi.unstubAllGlobals());

it("sends the answer to that Question of the round and returns the API's result", async () => {
  const marked = { correct: false, round: { answered: 1 } };
  const fetch = vi.fn(async () => Response.json(marked));
  vi.stubGlobal("fetch", fetch);

  const result = await answerReviewQuestion("agentic-ai-engineer", "round-1", "w01-l01-q01", "b");

  expect(result).toEqual(marked);
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/stacks/agentic-ai-engineer/review/rounds/round-1/answers",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ question_id: "w01-l01-q01", answer: "b" }),
    }),
  );
});

it("returns the grading failure instead of throwing, so the round can offer to resubmit", async () => {
  const detail = { code: "grading_failed", message: "Couldn't grade: submit again." };
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 503 })));

  await expect(answerReviewQuestion("s", "r", "q", "An answer.")).resolves.toEqual(detail);
});
