import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { DailyChallenge, TodaysChallenge } from "@/lib/api";
import { NEW_LEARNER, ONBOARDED, ONBOARDED_TWICE, stubApi } from "@/test/stubApi";
import Home from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("sends a first sign-in to onboarding", async () => {
  stubApi({ "/me": NEW_LEARNER });

  await expect(Home()).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining(";/onboarding;") }),
  );
});

it("gives each Active Stack its own card, linking to its Week map", async () => {
  stubApi({ "/me": ONBOARDED_TWICE });

  render(await Home());

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Your Stacks");
  const cards = [
    ["Agentic AI Engineer", "/stacks/agentic-ai-engineer"],
    ["Data Engineer", "/stacks/data-engineer"],
  ];
  for (const [name, href] of cards) {
    const card = screen.getByRole("region", { name });
    expect(within(card).getByRole("link", { name: "Week map" }).getAttribute("href")).toBe(href);
  }
  expect(screen.getByRole("link", { name: "Change Active Stacks" }).getAttribute("href")).toBe(
    "/settings",
  );
});

function today(
  stackId: string,
  stackName: string,
  challenge: Partial<DailyChallenge> | null,
  streak = 0,
): TodaysChallenge {
  return {
    stack_id: stackId,
    stack_name: stackName,
    day: "2026-09-27",
    streak,
    challenge: challenge && {
      number: 1,
      day: "2026-09-27",
      label: `${stackName} #1 · 27 Sep`,
      status: "not_started",
      score: null,
      out_of: null,
      result_card: null,
      max_answer_chars: 4000,
      questions: [],
      ...challenge,
    },
  };
}

it("shows each Active Stack's Challenge for today, or says there is none", async () => {
  stubApi({
    "/me": ONBOARDED_TWICE,
    "/stacks/agentic-ai-engineer/challenges/today": today(
      "agentic-ai-engineer",
      "Agentic AI Engineer",
      {},
    ),
    "/stacks/data-engineer/challenges/today": today("data-engineer", "Data Engineer", null),
  });

  render(await Home());

  const agentic = screen.getByRole("region", { name: "Agentic AI Engineer" });
  expect(within(agentic).getByText("Agentic AI Engineer #1 · 27 Sep")).toBeTruthy();
  expect(within(agentic).getByRole("link", { name: "Play" }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer/challenge",
  );
  const data = screen.getByRole("region", { name: "Data Engineer" });
  expect(within(data).getByText("No Challenge today")).toBeTruthy();
  expect(within(data).queryByRole("link", { name: "Play" })).toBeNull();
});

it("says when today's Challenge couldn't be loaded, instead of \"No Challenge today\"", async () => {
  const fetch = stubApi({ "/me": ONBOARDED_TWICE });
  const stubbed = fetch.getMockImplementation()!;
  fetch.mockImplementation(async (url: string) =>
    new URL(url).pathname === "/stacks/data-engineer/challenges/today"
      ? Response.json({ detail: "boom" }, { status: 500 })
      : stubbed(url),
  );
  vi.spyOn(console, "error").mockImplementation(() => {});

  render(await Home());

  for (const name of ["Agentic AI Engineer", "Data Engineer"]) {
    const card = screen.getByRole("region", { name });
    expect(within(card).getByRole("alert").textContent).toContain("couldn't be loaded");
    expect(within(card).queryByText("No Challenge today")).toBeNull();
  }
});

it.each([
  [{ status: "in_progress" }, "Continue", null],
  [{ status: "finished", score: 2, out_of: 3 }, "Replay", "Played: 2/3"],
] as const)("offers to continue or replay today's Challenge", async (challenge, link, played) => {
  stubApi({
    "/me": ONBOARDED,
    "/stacks/agentic-ai-engineer/challenges/today": today(
      "agentic-ai-engineer",
      "Agentic AI Engineer",
      challenge,
    ),
  });

  render(await Home());

  const card = screen.getByRole("region", { name: "Agentic AI Engineer" });
  expect(within(card).getByRole("link", { name: link }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer/challenge",
  );
  if (played) expect(within(card).getByText(played, { exact: false })).toBeTruthy();
});

it("shows each Active Stack's own Streak", async () => {
  stubApi({
    "/me": ONBOARDED_TWICE,
    "/stacks/agentic-ai-engineer/challenges/today": today(
      "agentic-ai-engineer",
      "Agentic AI Engineer",
      {},
      3,
    ),
    "/stacks/data-engineer/challenges/today": today("data-engineer", "Data Engineer", null, 0),
  });

  render(await Home());

  const agentic = screen.getByRole("region", { name: "Agentic AI Engineer" });
  expect(within(agentic).getByText("🔥 3-Day Streak")).toBeTruthy();
  const data = screen.getByRole("region", { name: "Data Engineer" });
  expect(within(data).getByText("No Streak running")).toBeTruthy();
  expect(within(data).queryByText(/🔥/)).toBeNull();
});

it("links to Review, one page across every Active Stack", async () => {
  stubApi({ "/me": ONBOARDED_TWICE });

  render(await Home());

  expect(screen.getByRole("link", { name: "Review" }).getAttribute("href")).toBe("/review");
});

it("links each Active Stack to its Archive", async () => {
  stubApi({ "/me": ONBOARDED_TWICE });

  render(await Home());

  const card = screen.getByRole("region", { name: "Data Engineer" });
  expect(within(card).getByRole("link", { name: "Archive" }).getAttribute("href")).toBe(
    "/stacks/data-engineer/archive",
  );
});

it("links to Catch-up with how many past Challenges aren't played, across Active Stacks", async () => {
  const stack = { challenges: [], stack_name: "" };
  stubApi({
    "/me": ONBOARDED_TWICE,
    "/catch-up": {
      stacks: [
        { ...stack, stack_id: "agentic-ai-engineer", count: 2 },
        { ...stack, stack_id: "data-engineer", count: 1 },
      ],
    },
  });

  render(await Home());

  expect(screen.getByRole("link", { name: "Catch-up" }).getAttribute("href")).toBe("/catch-up");
  expect(screen.getByText(/3 past Challenges you haven't played/)).toBeTruthy();
});

it("shows no Catch-up when there's nothing to catch up on", async () => {
  stubApi({ "/me": ONBOARDED, "/catch-up": { stacks: [] } });

  render(await Home());

  expect(screen.queryByRole("link", { name: "Catch-up" })).toBeNull();
});
