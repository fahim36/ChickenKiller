import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Milestone, MilestoneTick } from "@/lib/api";
import { MilestoneChecklist } from "./MilestoneChecklist";

const buildIt: Milestone = {
  id: "w01-m01",
  title: "Build a CLI",
  kind: "build",
  minutes: 120,
  ticked: false,
};
const apply: Milestone = {
  id: "w01-m02",
  title: "Apply to one job",
  kind: "job-hunt",
  minutes: 30,
  ticked: true,
};

/** Stands in for the server action: saves whatever it is asked to. */
function savingAction() {
  return vi.fn(
    async (id: string, ticked: boolean): Promise<MilestoneTick> => ({ id, ticked }),
  );
}

afterEach(cleanup);

const checkbox = (name: RegExp) => screen.getByRole("checkbox", { name }) as HTMLInputElement;

it("shows each Milestone with its kind and whether it's ticked", () => {
  render(<MilestoneChecklist milestones={[buildIt, apply]} tickAction={savingAction()} />);

  expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    "Build Build a CLI",
    "Job hunt Apply to one job",
  ]);
  expect([checkbox(/Build a CLI/).checked, checkbox(/Apply to one job/).checked]).toEqual([
    false,
    true,
  ]);
});

it("saves a tick", async () => {
  const tickAction = savingAction();
  render(<MilestoneChecklist milestones={[buildIt, apply]} tickAction={tickAction} />);

  fireEvent.click(checkbox(/Build a CLI/));

  await vi.waitFor(() => expect(tickAction).toHaveBeenCalledWith("w01-m01", true));
  expect(checkbox(/Build a CLI/).checked).toBe(true);
});

it("saves an untick", async () => {
  const tickAction = savingAction();
  render(<MilestoneChecklist milestones={[buildIt, apply]} tickAction={tickAction} />);

  fireEvent.click(checkbox(/Apply to one job/));

  await vi.waitFor(() => expect(tickAction).toHaveBeenCalledWith("w01-m02", false));
  expect(checkbox(/Apply to one job/).checked).toBe(false);
});

it("puts the tick back and says so when it can't be saved", async () => {
  const tickAction = vi.fn(async (): Promise<MilestoneTick> => {
    throw new Error("HTTP 500");
  });
  render(<MilestoneChecklist milestones={[buildIt]} tickAction={tickAction} />);

  fireEvent.click(checkbox(/Build a CLI/));

  expect((await screen.findByRole("alert")).textContent).toBe(
    "Couldn't save “Build a CLI”. Try again.",
  );
  expect(checkbox(/Build a CLI/).checked).toBe(false);
});
