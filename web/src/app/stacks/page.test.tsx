import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NEW_LEARNER, ONBOARDED, ONBOARDED_TWICE, STACKS, stubApi } from "@/test/stubApi";
import StacksPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("next/cache", () => ({ revalidatePath: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

const ticked = () =>
  (screen.getAllByRole("checkbox") as HTMLInputElement[])
    .filter((c) => c.checked)
    .map((c) => c.value);

it("starts from the Learner's Active Stacks", async () => {
  stubApi({ "/me": ONBOARDED, "/stacks": STACKS });

  render(await StacksPage());

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Your Active Stacks");
  expect(ticked()).toEqual(["agentic-ai-engineer"]);
  expect(screen.queryByRole("combobox")).toBeNull();
  expect(screen.getByRole("button", { name: "Save" })).toBeTruthy();
  expect(screen.getByText(/progress on each Stack is kept/)).toBeTruthy();
});

it("ticks every Active Stack", async () => {
  stubApi({ "/me": ONBOARDED_TWICE, "/stacks": STACKS });

  render(await StacksPage());

  expect(ticked()).toEqual(["agentic-ai-engineer", "data-engineer"]);
});

it("keeps a withdrawn Active Stack on the list so the Learner can keep it", async () => {
  stubApi({ "/me": ONBOARDED, "/stacks": STACKS.slice(1) });

  render(await StacksPage());

  expect(screen.getAllByRole("checkbox").map((r) => r.getAttribute("value"))).toEqual([
    "agentic-ai-engineer",
    "data-engineer",
  ]);
  expect(ticked()).toEqual(["agentic-ai-engineer"]);
});

it("sends a Learner who hasn't onboarded to onboarding", async () => {
  stubApi({ "/me": NEW_LEARNER, "/stacks": STACKS });

  await expect(StacksPage()).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining("/onboarding") }),
  );
});
