import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { InterviewPractice } from "./InterviewPractice";
import type { InterviewSession } from "./types";
import {
  saveInterviewResponse,
  startInterview,
  deleteInterview,
} from "./actions";

vi.mock("./actions", () => ({
  startInterview: vi.fn(),
  saveInterviewResponse: vi.fn(),
  deleteInterview: vi.fn(),
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const row: InterviewSession = {
  id: "private-id",
  stack_id: "python",
  expires_at: "2026-11-10T00:00:00Z",
  prompts: [
    {
      id: "scenario",
      concept: "aliases",
      lesson: "w01-l01",
      scenario: "Explain the race.",
      rubric: ["Coordinate shared updates."],
      misconceptions: ["Every lock is distributed."],
    },
  ],
  responses: {},
};

it("saves a response and shows reviewed guidance without an AI key", async () => {
  vi.mocked(startInterview).mockResolvedValue(row);
  vi.mocked(saveInterviewResponse).mockResolvedValue({
    ...row,
    responses: { scenario: "Use a token." },
  });
  vi.mocked(deleteInterview).mockResolvedValue(undefined);
  render(
    <InterviewPractice
      stack="python"
      topics={{
        topics: [
          { concept: "aliases", id: "scenario", scenario: "Explain the race." },
        ],
        lesson_id: "w01-l01",
        message: null,
      }}
      history={[]}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Start practice" }));
  await screen.findByRole("textbox");
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "Use a token." },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save and self-review" }));
  await screen.findByText("Coordinate shared updates.");
  expect(saveInterviewResponse).toHaveBeenCalledWith(
    "private-id",
    "scenario",
    "Use a token.",
  );
  expect(screen.getByRole("status").textContent).toContain("Practice complete");
  await waitFor(() =>
    expect(
      screen
        .getByRole("button", { name: "Delete session" })
        .hasAttribute("disabled"),
    ).toBe(false),
  );
  fireEvent.click(screen.getByRole("button", { name: "Delete session" }));
  await waitFor(() =>
    expect(screen.queryByText("Coordinate shared updates.")).toBeNull(),
  );
});

it("offers a Lesson when no reviewed topics are studied", () => {
  render(
    <InterviewPractice
      stack="python"
      topics={{
        topics: [],
        lesson_id: "w01-l01",
        message: "Study a topic first.",
      }}
      history={[]}
    />,
  );
  expect(
    screen.getByRole("link", { name: "Study the Lesson" }).getAttribute("href"),
  ).toBe("/stacks/python/lessons/w01-l01");
  expect(screen.queryByRole("button", { name: "Start practice" })).toBeNull();
});
