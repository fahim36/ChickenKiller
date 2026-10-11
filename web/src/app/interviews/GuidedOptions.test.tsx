import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { GuidedOptions } from "./GuidedOptions";
import { openInterviewTurn } from "./actions";
import type { InterviewPrompt, InterviewSession } from "./types";
vi.mock("./actions", () => ({ openInterviewTurn: vi.fn() }));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});
const prompt: InterviewPrompt = {
  id: "main",
  concept: "concurrency",
  lesson: "w01-l01",
  scenario: "Main scenario",
  rubric: ["Atomic update"],
  misconceptions: [],
  follow_ups: [
    { id: "replicas", scenario: "Explain replicas", rubric: ["Shared state"] },
    { id: "failure", scenario: "Explain failure", rubric: ["Recovery"] },
  ],
};
const session: InterviewSession = {
  id: "session",
  stack_id: "python",
  expires_at: "2026-11-11T00:00:00Z",
  prompts: [prompt],
  responses: { main: "Token." },
  turns: [],
};

it("offers reviewed self-review choices without claiming an AI selection", async () => {
  const onOpened = vi.fn();
  vi.mocked(openInterviewTurn).mockResolvedValue(session);
  render(
    <GuidedOptions session={session} prompt={prompt} onOpened={onOpened} />,
  );
  expect(screen.getByText(/Self-review: choose/)).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: /Explain replicas/ }));
  await waitFor(() => expect(onOpened).toHaveBeenCalledWith(session));
  expect(openInterviewTurn).toHaveBeenCalledWith(
    "session",
    "main",
    "follow_up",
    "replicas",
  );
});

it("uses only the reviewed choice already selected in AI feedback", () => {
  const assessed: InterviewSession = {
    ...session,
    operations: [
      {
        id: "operation",
        prompt_id: "main",
        state: "complete",
        feedback: {
          criteria: [],
          uncertainty: "Limited evidence",
          next_steps: [],
          follow_up: "replicas",
        },
      },
    ],
  };
  render(
    <GuidedOptions session={assessed} prompt={prompt} onOpened={vi.fn()} />,
  );
  expect(screen.getByText("AI selected this reviewed follow-up:")).toBeTruthy();
  expect(screen.getByRole("button", { name: /Explain replicas/ })).toBeTruthy();
  expect(screen.queryByRole("button", { name: /Explain failure/ })).toBeNull();
});

it("prevents further options once the one retry is used", () => {
  render(
    <GuidedOptions
      session={{
        ...session,
        turns: [
          {
            ...prompt,
            id: "retry",
            parent_id: "main",
            kind: "retry",
            seconds: 60,
          },
        ],
      }}
      prompt={prompt}
      onOpened={vi.fn()}
    />,
  );
  expect(screen.queryByRole("button")).toBeNull();
});
