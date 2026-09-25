import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { StackSummary } from "@/lib/api";
import { StackSettingsForm, type SettingsState } from "./StackSettingsForm";

const stacks: StackSummary[] = [
  { id: "agentic-ai-engineer", name: "Agentic AI Engineer", summary: "Agents.", version: "v1" },
  { id: "data-engineer", name: "Data Engineer", summary: "Pipelines.", version: "v1" },
];

/** The time zone the browser reports, as `Intl.DateTimeFormat().resolvedOptions()` does. */
function browserTimeZone(timeZone: string) {
  const real = Intl.DateTimeFormat.prototype.resolvedOptions;
  vi.spyOn(Intl.DateTimeFormat.prototype, "resolvedOptions").mockImplementation(function (
    this: Intl.DateTimeFormat,
  ) {
    return { ...real.call(this), timeZone };
  });
}

/** An action that records what was submitted. */
function recordingAction() {
  const sent: Record<string, string>[] = [];
  const action = vi.fn(async (_: SettingsState, form: FormData): Promise<SettingsState> => {
    sent.push(Object.fromEntries(form.entries()) as Record<string, string>);
    return null;
  });
  return { action, sent };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const timeZoneField = () => screen.getByRole("combobox", { name: "Time zone" }) as HTMLInputElement;

it("lists the published Stacks to choose from", () => {
  render(<StackSettingsForm stacks={stacks} action={recordingAction().action} submitLabel="Start" />);

  expect(screen.getAllByRole("radio").map((r) => r.getAttribute("value"))).toEqual([
    "agentic-ai-engineer",
    "data-engineer",
  ]);
  expect(screen.getByRole("radio", { name: /Agentic AI Engineer/ })).toBeTruthy();
});

it("pre-fills the time zone from the browser", () => {
  browserTimeZone("Asia/Dhaka");

  render(<StackSettingsForm stacks={stacks} action={recordingAction().action} submitLabel="Start" />);

  expect(timeZoneField().value).toBe("Asia/Dhaka");
});

it("sends the chosen Stack and a changed time zone", async () => {
  browserTimeZone("Asia/Dhaka");
  const { action, sent } = recordingAction();
  render(<StackSettingsForm stacks={stacks} action={action} submitLabel="Start studying" />);

  fireEvent.click(screen.getByRole("radio", { name: /Data Engineer/ }));
  fireEvent.change(timeZoneField(), { target: { value: "Europe/Berlin" } });
  fireEvent.click(screen.getByRole("button", { name: "Start studying" }));

  await vi.waitFor(() =>
    expect(sent).toEqual([{ active_stack_id: "data-engineer", time_zone: "Europe/Berlin" }]),
  );
});

it("starts from the saved Active Stack and time zone, not the browser's", () => {
  browserTimeZone("Asia/Dhaka");

  render(
    <StackSettingsForm
      stacks={stacks}
      action={recordingAction().action}
      submitLabel="Save"
      current={{ active_stack_id: "data-engineer", time_zone: "America/Los_Angeles" }}
    />,
  );

  expect((screen.getByRole("radio", { name: /Data Engineer/ }) as HTMLInputElement).checked).toBe(
    true,
  );
  expect(timeZoneField().value).toBe("America/Los_Angeles");
});

it("shows why the settings weren't saved", async () => {
  const action = vi.fn(
    async (): Promise<SettingsState> => ({ error: "Choose a time zone from the list." }),
  );
  render(<StackSettingsForm stacks={stacks} action={action} submitLabel="Save" />);

  fireEvent.click(screen.getByRole("radio", { name: /Agentic AI Engineer/ }));
  fireEvent.click(screen.getByRole("button", { name: "Save" }));

  expect((await screen.findByRole("alert")).textContent).toBe("Choose a time zone from the list.");
});
