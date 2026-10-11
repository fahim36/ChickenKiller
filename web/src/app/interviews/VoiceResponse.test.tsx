import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { VoiceResponse } from "./VoiceResponse";
import { DeviceSpeech } from "./DeviceSpeech";
import {
  confirmInterviewTranscript,
  transcribeInterviewAudio,
  loadInterviewAudio,
  uploadInterviewAudio,
} from "./actions";
import type { InterviewSession } from "./types";

vi.mock("./actions", () => ({
  cancelInterviewAudio: vi.fn(),
  confirmInterviewTranscript: vi.fn(),
  loadInterviewAudio: vi.fn(),
  transcribeInterviewAudio: vi.fn(),
  uploadInterviewAudio: vi.fn(),
}));
afterEach(() => {
  cleanup();
  vi.resetAllMocks();
  vi.unstubAllGlobals();
});
const initial = {
  id: "clip",
  prompt_id: "prompt",
  expires_at: new Date(Date.now() + 3600000).toISOString(),
  transcript: null,
};

it("keeps transcription unconfirmed until the learner corrects and confirms it", async () => {
  const row: InterviewSession = {
    id: "session",
    stack_id: "python",
    expires_at: initial.expires_at,
    prompts: [],
    responses: { prompt: "Use a token." },
  };
  vi.mocked(transcribeInterviewAudio).mockResolvedValue({
    ...initial,
    transcript: "Use a taken.",
    state: "complete",
  });
  vi.mocked(confirmInterviewTranscript).mockResolvedValue(row);
  const onConfirmed = vi.fn();
  render(
    <VoiceResponse
      sessionId="session"
      promptId="prompt"
      initial={initial}
      onConfirmed={onConfirmed}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Transcribe with my Gemini key" }),
  );
  await waitFor(() =>
    expect(screen.getByRole("textbox")).toHaveProperty("value", "Use a taken."),
  );
  expect(confirmInterviewTranscript).not.toHaveBeenCalled();
  fireEvent.change(screen.getByRole("textbox"), {
    target: { value: "Use a token." },
  });
  const confirm = screen.getByRole("button", {
    name: "Confirm transcript and delete audio",
  });
  await waitFor(() => expect(confirm.hasAttribute("disabled")).toBe(false));
  fireEvent.click(confirm);
  await waitFor(() => expect(onConfirmed).toHaveBeenCalledWith(row));
  expect(confirmInterviewTranscript).toHaveBeenCalledWith(
    "session",
    "clip",
    "prompt",
    "Use a token.",
  );
  expect(screen.queryByRole("textbox")).toBeNull();
});

it("leaves playback and correction available when transcription quota fails", async () => {
  vi.mocked(transcribeInterviewAudio).mockResolvedValue({
    ...initial,
    state: "quota_exhausted",
  });
  render(
    <VoiceResponse
      sessionId="session"
      promptId="prompt"
      initial={initial}
      onConfirmed={vi.fn()}
    />,
  );
  fireEvent.click(
    screen.getByRole("button", { name: "Transcribe with my Gemini key" }),
  );
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    expect.stringContaining("quota_exhausted"),
  );
  expect(screen.getByRole("button", { name: "Load playback" })).toBeTruthy();
  expect(screen.getByRole("textbox")).toHaveProperty("value", "");
  expect(confirmInterviewTranscript).not.toHaveBeenCalled();
});

it("explains microphone refusal and keeps the typing fallback", async () => {
  vi.stubGlobal("MediaRecorder", class {});
  const getUserMedia = vi
    .fn()
    .mockRejectedValue(new Error("Permission denied"));
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: { getUserMedia },
  });
  render(
    <VoiceResponse
      sessionId="session"
      promptId="prompt"
      onConfirmed={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Start recording" }));
  expect(await screen.findByRole("alert")).toHaveProperty(
    "textContent",
    expect.stringContaining("refused"),
  );
  expect(screen.getByRole("status").textContent).toBe("Microphone off");
});

it("keeps visible content usable without device speech", () => {
  vi.stubGlobal("speechSynthesis", undefined);
  render(<DeviceSpeech text="Explain the race." />);
  fireEvent.click(screen.getByRole("button", { name: "Read aloud" }));
  expect(screen.getByRole("status").textContent).toContain(
    "Read the visible text",
  );
});

it("clears the old playback when loading a replacement fails", async () => {
  class Recorder {
    static isTypeSupported() {
      return true;
    }
    state = "inactive";
    mimeType = "audio/webm";
    ondataavailable: ((event: { data: Blob }) => void) | null = null;
    onstop: (() => void) | null = null;
    start() {
      this.state = "recording";
    }
    stop() {
      this.state = "inactive";
      this.ondataavailable?.({
        data: new Blob(["replacement"], { type: this.mimeType }),
      });
      this.onstop?.();
    }
  }
  vi.stubGlobal("MediaRecorder", Recorder);
  Object.defineProperty(navigator, "mediaDevices", {
    configurable: true,
    value: {
      getUserMedia: vi
        .fn()
        .mockResolvedValue({ getTracks: () => [{ stop: vi.fn() }] }),
    },
  });
  vi.mocked(loadInterviewAudio)
    .mockResolvedValueOnce({ mime: "audio/webm", data: "b2xk" })
    .mockRejectedValueOnce(new Error("Unavailable"));
  vi.mocked(uploadInterviewAudio).mockResolvedValue({
    ...initial,
    id: "replacement",
  });
  render(
    <VoiceResponse
      sessionId="session"
      promptId="prompt"
      initial={initial}
      onConfirmed={vi.fn()}
    />,
  );
  fireEvent.click(screen.getByRole("button", { name: "Load playback" }));
  await screen.findByLabelText("Your temporary response recording");
  const replace = screen.getByRole("button", { name: "Replace recording" });
  await waitFor(() => expect(replace.hasAttribute("disabled")).toBe(false));
  fireEvent.click(replace);
  fireEvent.click(
    await screen.findByRole("button", { name: "Stop recording" }),
  );
  await screen.findByRole("alert");
  expect(
    screen.queryByLabelText("Your temporary response recording"),
  ).toBeNull();
});
