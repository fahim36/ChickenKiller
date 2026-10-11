import { cleanup, fireEvent, render, screen } from "@testing-library/react";
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
  expect(
    screen.getByRole("group", { name: "What does is compare?" }),
  ).toBeTruthy();
  expect(
    screen.getByText("Agentic AI Engineer · Question 1 of 1"),
  ).toBeTruthy();
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

it("requests the selected Concept and preserves it for the next set", async () => {
  const fetch = stubApi({ "/review": set });
  render(
    await ReviewPage({
      searchParams: Promise.resolve({
        stack_id: "agentic-ai-engineer",
        concept_id: "identity",
      }),
    }),
  );
  expect(fetch).toHaveBeenCalledWith(
    "http://localhost:8000/review?stack_id=agentic-ai-engineer&concept_id=identity",
    expect.anything(),
  );
  expect(screen.getByText(/only Questions currently due/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /Skip/ }));
  expect(
    screen.getByRole("link", { name: /Next set/ }).getAttribute("href"),
  ).toBe("/review?stack_id=agentic-ai-engineer&concept_id=identity");
});

it("does not turn an incomplete target into unrestricted practice", async () => {
  const fetch = stubApi({ "/review": set });
  render(
    await ReviewPage({
      searchParams: Promise.resolve({ concept_id: "identity" }),
    }),
  );
  expect(screen.getByText(/Select a Stack and Concept together/)).toBeTruthy();
  expect(fetch).not.toHaveBeenCalled();
});

it("distinguishes unavailable Review from an empty due queue", async () => {
  stubApi({});
  render(await ReviewPage());
  expect(screen.getByText(/Review couldn't be loaded/)).toBeTruthy();
});
