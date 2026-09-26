import { afterEach, expect, it, vi } from "vitest";
import { answerChallengeQuestion } from "./actions";

vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => vi.unstubAllGlobals());

it("sends the answer to that Question of the numbered Challenge and returns the result", async () => {
  const marked = { counted: true, outcome: "wrong", question: { id: "c001-q01" } };
  const fetch = vi.fn(async () => Response.json(marked));
  vi.stubGlobal("fetch", fetch);

  const result = await answerChallengeQuestion("agentic-ai-engineer", 1, "c001-q01", "b");

  expect(result).toEqual(marked);
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/stacks/agentic-ai-engineer/challenges/1/answers",
    expect.objectContaining({
      method: "POST",
      body: JSON.stringify({ question_id: "c001-q01", answer: "b" }),
    }),
  );
});

it("returns the grading failure instead of throwing, so the Learner can send it again", async () => {
  const detail = { code: "grading_failed", message: "Couldn't grade: submit again." };
  vi.stubGlobal("fetch", vi.fn(async () => Response.json({ detail }, { status: 503 })));

  await expect(answerChallengeQuestion("s", 1, "q", "An answer.")).resolves.toEqual(detail);
});
