import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import type { DailyReview, ReviewRoundSummary } from "@/lib/api";
import { DailyReviewBanner } from "./DailyReviewBanner";

afterEach(cleanup);

const round: ReviewRoundSummary = {
  id: "round-1",
  number: 1,
  state: "optional",
  opened_at: "2026-09-26T04:00:00Z",
  pending_at: "2026-09-26T06:00:00Z",
  finished_at: null,
  answered: 3,
  total: 10,
};

function renderBanner(
  changes: Partial<ReviewRoundSummary>,
  now = "2026-09-26T04:25:00Z",
  review: Partial<DailyReview> = {},
) {
  const daily: DailyReview = {
    day: "2026-09-26",
    time_zone: "Asia/Dhaka",
    rounds: [{ ...round, ...changes }],
    next_round_at: null,
    ...review,
  };
  render(<DailyReviewBanner review={daily} stackId="agentic-ai-engineer" now={new Date(now)} />);
  return screen.getByRole("region", { name: "Daily Review" });
}

it("offers an optional round with how long it stays optional", () => {
  const banner = renderBanner({});

  expect(banner.textContent).toContain("Review Round 1 is open: 7 of 10 Questions left.");
  expect(banner.textContent).toContain("Optional for another 1 h 35 min");
  expect(screen.getByRole("link", { name: "Continue the Review Round" }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer/review",
  );
});

it("says a pending round locks the next Lesson until it's finished", () => {
  const banner = renderBanner({ state: "pending", answered: 0 }, "2026-09-26T07:00:00Z");

  expect(banner.textContent).toContain(
    "Review Round 1 is pending: finish it to unlock your next Lesson.",
  );
  expect(screen.getByRole("link", { name: "Start the Review Round" })).toBeTruthy();
});

it("shows the latest round of the day, such as a pending Round 2", () => {
  const finished = { ...round, state: "finished" as const, answered: 10 };
  const second = { ...round, id: "round-2", number: 2, state: "pending" as const, answered: 0 };
  const banner = renderBanner({}, "2026-09-26T10:00:00Z", { rounds: [finished, second] });

  expect(banner.textContent).toContain(
    "Review Round 2 is pending: finish it to unlock your next Lesson.",
  );
});

it("says when the next round opens, in the Learner's time zone", () => {
  const banner = renderBanner({ state: "finished", answered: 10 }, "2026-09-26T04:25:00Z", {
    next_round_at: "2026-09-26T08:25:00Z",
  });

  expect(banner.textContent).toBe(
    "Review Round 1 is done. Review Round 2 opens at 14:25, in 4 h.",
  );
  expect(screen.queryByRole("link")).toBeNull();
});

it("says the Daily Review is done when no round is left to open today", () => {
  const banner = renderBanner({ number: 3, state: "finished", answered: 10 });

  expect(banner.textContent).toBe("Your Daily Review is done for today.");
  expect(screen.queryByRole("link")).toBeNull();
});
