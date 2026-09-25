import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { NEW_LEARNER, ONBOARDED, STACKS, stubApi } from "@/test/stubApi";
import OnboardingPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("next/cache", () => ({ revalidatePath: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

it("offers a new Learner the published Stacks and their time zone", async () => {
  stubApi({ "/me": NEW_LEARNER, "/stacks": STACKS });

  render(await OnboardingPage());

  expect(screen.getByRole("heading", { level: 1 }).textContent).toBe("Pick your Stack");
  expect(screen.getAllByRole("radio").map((r) => r.getAttribute("value"))).toEqual([
    "agentic-ai-engineer",
    "data-engineer",
  ]);
  expect(screen.getByRole("combobox", { name: "Time zone" })).toBeTruthy();
  expect(screen.getByRole("button", { name: "Start studying" })).toBeTruthy();
});

it("sends a returning Learner straight to their Active Stack", async () => {
  stubApi({ "/me": ONBOARDED, "/stacks": STACKS });

  await expect(OnboardingPage()).rejects.toThrow(
    expect.objectContaining({ digest: expect.stringContaining("/stacks/agentic-ai-engineer") }),
  );
});

it("says so when no Stack is published yet", async () => {
  stubApi({ "/me": NEW_LEARNER, "/stacks": [] });

  render(await OnboardingPage());

  expect(screen.getByText(/No Stack is published yet/)).toBeTruthy();
  expect(screen.queryByRole("button")).toBeNull();
});
