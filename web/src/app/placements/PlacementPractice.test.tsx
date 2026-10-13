import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { PlacementPractice } from "./PlacementPractice";
import { savePlacement, abandonPlacement, submitPlacement } from "./actions";
import type { PlacementAttempt } from "./types";

vi.mock("./actions", () => ({
  savePlacement: vi.fn(),
  abandonPlacement: vi.fn(),
  submitPlacement: vi.fn(),
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const attempt: PlacementAttempt = {
  id: "attempt",
  stack_id: "stack",
  week_id: "w01",
  state: "open",
  reason: null,
  questions: [
    {
      id: "q1",
      lesson: "l1",
      type: "multiple_choice",
      prompt: "Which boundary?",
      choices: [
        { id: "a", text: "Shared store" },
        { id: "b", text: "Process" },
      ],
    },
  ],
  responses: { q1: "b" },
  result: null,
};

it("restores saved selection and autosaves edits without revealing correctness", async () => {
  vi.mocked(savePlacement).mockResolvedValue(attempt);
  render(<PlacementPractice initial={attempt} />);
  expect((screen.getByLabelText("Process") as HTMLInputElement).checked).toBe(
    true,
  );
  fireEvent.click(screen.getByLabelText("Shared store"));
  await waitFor(() =>
    expect(savePlacement).toHaveBeenCalledWith("attempt", "q1", "a"),
  );
  await waitFor(() =>
    expect(screen.getByRole("status").textContent).toBe("Answers saved"),
  );
  expect(screen.queryByText("Correct")).toBeNull();
});

it("keeps a failed save visible and retries the selected answer", async () => {
  vi.mocked(savePlacement)
    .mockRejectedValueOnce(Error("offline"))
    .mockResolvedValue(attempt);
  render(<PlacementPractice initial={attempt} />);
  fireEvent.click(screen.getByLabelText("Shared store"));
  await screen.findByRole("alert");
  fireEvent.click(screen.getByText("Retry saving"));
  await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  expect(savePlacement).toHaveBeenCalledTimes(2);
});

it("shows cancellation returned while saving and removes answer controls", async () => {
  vi.mocked(savePlacement).mockResolvedValue({
    ...attempt,
    state: "cancelled",
    reason: "Teaching changed",
  });
  render(<PlacementPractice initial={attempt} />);
  fireEvent.click(screen.getByLabelText("Shared store"));
  await screen.findByText("Teaching changed");
  expect(screen.queryByRole("radio")).toBeNull();
});

it("abandonment preserves the terminal reason", async () => {
  vi.mocked(abandonPlacement).mockResolvedValue({
    ...attempt,
    state: "abandoned",
    reason: "Viewed Questions remain seen",
  });
  render(<PlacementPractice initial={attempt} />);
  fireEvent.click(screen.getByText("Abandon attempt"));
  await screen.findByText("Viewed Questions remain seen");
});

it("shows final per-Lesson results and explanations after submission", async () => {
  vi.mocked(submitPlacement).mockResolvedValue({
    ...attempt,
    state: "submitted",
    questions: [
      {
        ...attempt.questions[0],
        answer: "b",
        explanation: "Separate process boundary",
      },
    ],
    result: {
      passed: false,
      correct: 0,
      total: 1,
      lessons: [{ lesson: "l1", correct: 0, total: 1, passed: false }],
      correct_questions: { q1: false },
    },
  });
  render(<PlacementPractice initial={attempt} />);
  fireEvent.click(screen.getByText("Submit placement"));
  await screen.findByText("Separate process boundary");
  expect(screen.getByText("Lesson 1: 0/1 · Below 80%")).toBeTruthy();
  expect(screen.queryByRole("radio")).toBeNull();
});
