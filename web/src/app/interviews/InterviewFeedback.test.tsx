import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { InterviewFeedback } from "./InterviewFeedback";
import { requestInterviewFeedback } from "./actions";
vi.mock("./actions", () => ({ requestInterviewFeedback: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it("requires text confirmation and preserves self-review on quota exhaustion", async () => {
  vi.mocked(requestInterviewFeedback).mockResolvedValue({
    id: "id",
    prompt_id: "p",
    state: "quota_exhausted",
    feedback: null,
  });
  render(<InterviewFeedback sessionId="s" promptId="p" text="Use a token." />);
  const button = screen.getByRole("button", { name: "Request AI feedback" });
  expect(button.hasAttribute("disabled")).toBe(true);
  fireEvent.click(screen.getByRole("checkbox"));
  fireEvent.click(button);
  await screen.findByRole("status");
  expect(screen.getByRole("status").textContent).toContain(
    "reviewed rubric remain available",
  );
  expect(requestInterviewFeedback).toHaveBeenCalledTimes(1);
  expect(requestInterviewFeedback).toHaveBeenCalledWith(
    "s",
    expect.any(String),
    "p",
    true,
  );
});
