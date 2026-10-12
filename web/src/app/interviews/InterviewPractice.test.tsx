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
  openInterviewTurn,
  loadInterviewSession,
  transcribeInterviewAudio,
} from "./actions";

vi.mock("./actions", () => ({
  startInterview: vi.fn(),
  saveInterviewResponse: vi.fn(),
  deleteInterview: vi.fn(),
  openInterviewTurn: vi.fn(),
  loadInterviewSession: vi.fn(),
  transcribeInterviewAudio: vi.fn(),
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

it("refreshes charged attempts after transcription before transcript confirmation", async () => {
  const clip = {
    id: "clip", prompt_id: "scenario", transcript: null,
    expires_at: new Date(Date.now() + 3600000).toISOString(),
  };
  const active = { ...row, recordings: [clip], operations: [] };
  vi.mocked(startInterview).mockResolvedValue(active);
  vi.mocked(transcribeInterviewAudio).mockResolvedValue({
    ...clip, transcript: "Use a token.", state: "complete",
  });
  vi.mocked(loadInterviewSession).mockResolvedValue({
    ...active,
    operations: [{ id: "operation", prompt_id: "scenario", kind: "transcription", state: "complete", feedback: null }],
  });
  render(<InterviewPractice stack="python" topics={{ topics: [], lesson_id: null, message: null }} history={[]} />);
  fireEvent.click(screen.getByRole("button", { name: "Start practice" }));
  const transcribe = await screen.findByRole("button", { name: "Transcribe with my Gemini key" });
  fireEvent.click(transcribe);
  await screen.findByText(/1 of 18 provider attempts used/);
  expect(screen.getByLabelText("Confirm or correct your transcript")).toHaveProperty("value", "Use a token.");
  expect(screen.getByRole("button", { name: "Confirm transcript and delete audio" })).toBeTruthy();
});

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

it("keeps a main draft when an earlier optional turn is opened and skipped", async () => {
  const first = {
    ...row.prompts[0],
    follow_ups: [
      {
        id: "replicas",
        scenario: "Explain replicas",
        rubric: ["Shared state"],
      },
    ],
  };
  const second = {
    ...row.prompts[0],
    id: "second",
    scenario: "Next main scenario",
  };
  const started = {
    ...row,
    prompts: [first, second],
    responses: { scenario: "Token." },
  };
  const turn = {
    ...first,
    id: "follow",
    parent_id: first.id,
    kind: "follow_up" as const,
    seconds: 45 as const,
  };
  vi.mocked(startInterview).mockResolvedValue(started);
  vi.mocked(openInterviewTurn).mockResolvedValue({ ...started, turns: [turn] });
  vi.mocked(saveInterviewResponse).mockResolvedValue({
    ...started,
    turns: [turn],
    responses: { ...started.responses, follow: null },
  });
  render(
    <InterviewPractice
      stack="python"
      topics={{
        topics: [
          { id: "scenario", concept: "aliases", scenario: "Explain the race." },
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
    target: { value: "My unfinished main answer" },
  });
  fireEvent.click(
    screen.getByRole("button", {
      name: /Explain replicas.*Practice follow-up/,
    }),
  );
  await screen.findByRole("button", { name: "Skip optional turn" });
  fireEvent.click(screen.getByRole("button", { name: "Skip optional turn" }));
  await waitFor(() =>
    expect(screen.getByRole("textbox")).toHaveProperty(
      "value",
      "My unfinished main answer",
    ),
  );
});

it("reloads history and preserves reviewed self-review when content changed", async () => {
  vi.mocked(loadInterviewSession).mockResolvedValue({
    ...row,
    practice_state: "content_changed",
    ai_enabled: false,
  });
  render(
    <InterviewPractice
      stack="python"
      topics={{ topics: [], lesson_id: null, message: "Study first" }}
      history={[row]}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: /Open session/ }));
  expect(await screen.findByRole("status")).toHaveProperty(
    "textContent",
    expect.stringContaining("content changed"),
  );
  expect(loadInterviewSession).toHaveBeenCalledWith("private-id");
  expect(screen.getByText("Coordinate shared updates.")).toBeTruthy();
  expect(screen.queryByRole("textbox")).toBeNull();
});
