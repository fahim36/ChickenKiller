import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { ReviewSet } from "@/lib/api";
import { stubApi } from "@/test/stubApi";
import ReviewPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

const set: ReviewSet = {
  size: 10,
  max_answer_chars: 4000,
  questions: [
    {
      stack_id: "agentic-ai-engineer",
      stack_name: "Agentic AI Engineer",
      id: "w01-l01-q01",
      type: "multiple_choice",
      prompt: "What does `is` compare?",
      choices: [
        { id: "a", text: "Identity" },
        { id: "b", text: "Equality" },
      ],
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function renderReview(body: ReviewSet) {
  stubApi({ "/review": body });
  render(await ReviewPage());
}

it("asks the set's first Question, saying which Stack it is from", async () => {
  await renderReview(set);

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Review");
  expect(screen.getByRole("group", { name: "What does is compare?" })).toBeTruthy();
  expect(screen.getByText("Agentic AI Engineer · Question 1 of 1")).toBeTruthy();
});

it("says Review is optional and blocks nothing", async () => {
  await renderReview(set);

  expect(screen.getByText(/Optional: practise whenever you like/)).toBeTruthy();
});

it("says so when there is nothing to review", async () => {
  await renderReview({ ...set, questions: [] });

  expect(screen.getByRole("status").textContent).toBe(
    "Nothing to review right now. Missed Questions and Questions from your Completed Lessons come back here.",
  );
  expect(screen.queryByRole("group")).toBeNull();
});
