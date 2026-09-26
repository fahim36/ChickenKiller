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

function renderBanner(changes: Partial<ReviewRoundSummary>, now = "2026-09-26T04:25:00Z") {
  const review: DailyReview = { day: "2026-09-26", rounds: [{ ...round, ...changes }] };
  render(<DailyReviewBanner review={review} stackId="agentic-ai-engineer" now={new Date(now)} />);
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

it("says when today's rounds are done, with nothing to start", () => {
  const banner = renderBanner({ state: "finished", answered: 10 });

  expect(banner.textContent).toContain("Review Round 1 is done for today.");
  expect(screen.queryByRole("link")).toBeNull();
});
