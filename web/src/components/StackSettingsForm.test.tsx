import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { StackSummary } from "@/lib/api";
import { StackSettingsForm, type SettingsState } from "./StackSettingsForm";

const stacks: StackSummary[] = [
  { id: "agentic-ai-engineer", name: "Agentic AI Engineer", summary: "Agents.", version: "v1" },
  { id: "data-engineer", name: "Data Engineer", summary: "Pipelines.", version: "v1" },
];

/** An action that records the Stacks submitted. */
function recordingAction() {
  const sent: string[][] = [];
  const action = vi.fn(async (_: SettingsState, form: FormData): Promise<SettingsState> => {
    sent.push(form.getAll("stack_ids").map(String));
    return null;
  });
  return { action, sent };
}

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const box = (name: RegExp) => screen.getByRole("checkbox", { name }) as HTMLInputElement;

it("lists the published Stacks to choose from, none ticked yet", () => {
  render(<StackSettingsForm stacks={stacks} action={recordingAction().action} submitLabel="Start" />);

  expect(screen.getAllByRole("checkbox").map((r) => r.getAttribute("value"))).toEqual([
    "agentic-ai-engineer",
    "data-engineer",
  ]);
  expect(box(/Agentic AI Engineer/).checked).toBe(false);
});

it("ticks the only Stack when there is just one", () => {
  render(
    <StackSettingsForm stacks={stacks.slice(0, 1)} action={recordingAction().action} submitLabel="Start" />,
  );

  expect(box(/Agentic AI Engineer/).checked).toBe(true);
});

it("sends every ticked Stack", async () => {
  const { action, sent } = recordingAction();
  render(<StackSettingsForm stacks={stacks} action={action} submitLabel="Start studying" />);

  fireEvent.click(box(/Agentic AI Engineer/));
  fireEvent.click(box(/Data Engineer/));
  fireEvent.click(screen.getByRole("button", { name: "Start studying" }));

  await vi.waitFor(() => expect(sent).toEqual([["agentic-ai-engineer", "data-engineer"]]));
});

it("starts from the Learner's Active Stacks, and an unticked one is left out", async () => {
  const { action, sent } = recordingAction();
  render(
    <StackSettingsForm
      stacks={stacks}
      action={action}
      submitLabel="Save"
      current={["agentic-ai-engineer", "data-engineer"]}
    />,
  );
  expect(box(/Data Engineer/).checked).toBe(true);

  fireEvent.click(box(/Agentic AI Engineer/));
  fireEvent.click(screen.getByRole("button", { name: "Save" }));

  await vi.waitFor(() => expect(sent).toEqual([["data-engineer"]]));
});

it("shows why the Stacks weren't saved", async () => {
  const action = vi.fn(async (): Promise<SettingsState> => ({ error: "Pick at least one Stack." }));
  render(<StackSettingsForm stacks={stacks} action={action} submitLabel="Save" />);

  fireEvent.click(screen.getByRole("button", { name: "Save" }));

  expect((await screen.findByRole("alert")).textContent).toBe("Pick at least one Stack.");
});
