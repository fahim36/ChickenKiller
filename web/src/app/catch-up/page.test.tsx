import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { CatchUp } from "@/lib/api";
import { stubApi } from "@/test/stubApi";
import CatchUpPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const CATCH_UP: CatchUp = {
  stacks: [
    {
      stack_id: "agentic-ai-engineer",
      stack_name: "Agentic AI Engineer",
      count: 2,
      challenges: [
        {
          number: 2,
          day: "2026-09-26",
          label: "Agentic AI Engineer #2 · 26 Sep",
          status: "in_progress",
          score: null,
          out_of: null,
        },
        {
          number: 1,
          day: "2026-09-25",
          label: "Agentic AI Engineer #1 · 25 Sep",
          status: "not_started",
          score: null,
          out_of: null,
        },
      ],
    },
    {
      stack_id: "data-engineer",
      stack_name: "Data Engineer",
      count: 0,
      challenges: [],
    },
  ],
};

it("lists the unplayed past Challenges of each Active Stack, with a count", async () => {
  stubApi({ "/catch-up": CATCH_UP });

  render(await CatchUpPage());

  const agentic = screen.getByRole("region", {
    name: "Agentic AI Engineer (2)",
  });
  expect(within(agentic).getByRole("link", { name: "Play #1 · 25 Sep" }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer/archive/1",
  );
  expect(within(agentic).getByRole("link", { name: "Continue #2 · 26 Sep" })).toBeTruthy();
  expect(screen.queryByRole("region", { name: /Data Engineer/ })).toBeNull();
  expect(screen.getByText(/Optional/)).toBeTruthy();
});

it("says so when there's nothing to catch up on", async () => {
  stubApi({ "/catch-up": { stacks: [{ ...CATCH_UP.stacks[1] }] } });

  render(await CatchUpPage());

  expect(screen.getByRole("status").textContent).toBe("You're all caught up.");
});
