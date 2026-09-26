import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { DailyReviewDetail, ReviewRound } from "@/lib/api";
import { stubApi } from "@/test/stubApi";
import DailyReviewPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

const round: ReviewRound = {
  id: "round-1",
  number: 1,
  state: "pending",
  opened_at: "2026-09-26T04:00:00Z",
  pending_at: "2026-09-26T06:00:00Z",
  finished_at: null,
  answered: 0,
  total: 1,
  max_answer_chars: 4000,
  remaining: [
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
  results: [],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function renderReview(review: DailyReviewDetail) {
  stubApi({ "/stacks/agentic-ai-engineer/review": review });
  const params = Promise.resolve({ stackId: "agentic-ai-engineer" });
  render(await DailyReviewPage({ params } as never));
}

it("shows the round waiting to be answered, and says when it's pending", async () => {
  await renderReview({ day: "2026-09-26", rounds: [round], current: round });

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Review Round 1");
  expect(screen.getByText(/your next Lesson unlocks once it's finished/)).toBeTruthy();
  expect(screen.getByRole("group", { name: "What does is compare?" })).toBeTruthy();
});

it("says today's round is done when nothing is left to answer", async () => {
  const done = { ...round, state: "finished" as const, answered: 1 };
  await renderReview({ day: "2026-09-26", rounds: [done], current: null });

  expect(screen.getByRole("status").textContent).toBe("Today's Review Round is done.");
});

it("says there is no Daily Review on a day with nothing owed", async () => {
  await renderReview({ day: "2026-09-26", rounds: [], current: null });

  expect(screen.getByRole("status").textContent).toContain("No Daily Review today");
});
