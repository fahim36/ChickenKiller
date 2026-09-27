import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { StackChallenge } from "@/lib/api";
import { stubApi } from "@/test/stubApi";
import ArchivedChallengePage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const PATH = "/stacks/agentic-ai-engineer/challenges/1";

const PAST: StackChallenge = {
  stack_id: "agentic-ai-engineer",
  stack_name: "Agentic AI Engineer",
  day: "2026-09-27",
  challenge: {
    number: 1,
    day: "2026-09-25",
    label: "Agentic AI Engineer #1 · 25 Sep",
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

async function renderPage(body: StackChallenge | null, number = "1") {
  stubApi(body ? { [PATH]: body } : {});
  render(
    await ArchivedChallengePage({
      params: Promise.resolve({ stackId: "agentic-ai-engineer", number }),
    } as never),
  );
}

it("plays a past Challenge like today's, saying it doesn't count toward a Streak", async () => {
  await renderPage(PAST);

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe(
    "Agentic AI Engineer #1 · 25 Sep",
  );
  expect(screen.getByText(/doesn't count toward your Streak/)).toBeTruthy();
  expect(screen.getByRole("group", { name: "What does is compare?" })).toBeTruthy();
  expect(screen.getByRole("link", { name: "Archive" }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer/archive",
  );
});

it("says nothing about the Streak for today's Challenge, which counts as usual", async () => {
  await renderPage({
    ...PAST,
    challenge: { ...PAST.challenge, day: "2026-09-27" },
  });

  expect(screen.queryByText(/Streak/)).toBeNull();
});

it("shows a played Challenge's first result, with a replay", async () => {
  await renderPage({
    ...PAST,
    challenge: {
      ...PAST.challenge,
      status: "finished",
      score: 0,
      out_of: 0,
      questions: [],
    },
  });

  expect(screen.getByText("Played: 0/0")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Replay" })).toBeTruthy();
});

it("is a 404 for a Challenge that isn't released, or isn't a number", async () => {
  await expect(renderPage(null)).rejects.toThrow(
    expect.objectContaining({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" }),
  );
  await expect(renderPage(PAST, "today")).rejects.toThrow(
    expect.objectContaining({ digest: "NEXT_HTTP_ERROR_FALLBACK;404" }),
  );
});
