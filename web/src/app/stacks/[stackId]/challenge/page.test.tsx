import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { TodaysChallenge } from "@/lib/api";
import { stubApi } from "@/test/stubApi";
import ChallengePage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

const PATH = "/stacks/agentic-ai-engineer/challenges/today";

const TODAY: TodaysChallenge = {
  stack_id: "agentic-ai-engineer",
  stack_name: "Agentic AI Engineer",
  day: "2026-09-27",
  streak: 0,
  challenge: {
    number: 1,
    day: "2026-09-27",
    label: "Agentic AI Engineer #1 · 27 Sep",
    status: "not_started",
    score: null,
    out_of: null,
    result_card: null,
    max_answer_chars: 4000,
    questions: [
      {
        id: "c001-q01",
        type: "multiple_choice",
        prompt: "What does `is` compare?",
        choices: [
          { id: "a", text: "Identity" },
          { id: "b", text: "Equality" },
        ],
        retired: false,
        retired_reason: null,
        replaced_by: null,
        outcome: null,
        answered: null,
      },
    ],
  },
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function renderPage(body: TodaysChallenge) {
  stubApi({ [PATH]: body });
  render(
    await ChallengePage({ params: Promise.resolve({ stackId: "agentic-ai-engineer" }) } as never),
  );
}

it("names today's Challenge by number and UTC date, and asks its first Question", async () => {
  await renderPage(TODAY);

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
    "Agentic AI Engineer #1 · 27 Sep",
  );
  expect(screen.getByRole("group", { name: "What does is compare?" })).toBeTruthy();
});

it("says so when no Challenge is written for today", async () => {
  await renderPage({ ...TODAY, challenge: null });

  expect(screen.getByRole("status").textContent).toBe(
    "No Challenge today. Check back tomorrow.",
  );
  expect(screen.queryByRole("group")).toBeNull();
});
