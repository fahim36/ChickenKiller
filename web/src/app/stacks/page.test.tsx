import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { StackPlan } from "@/lib/api";
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

const BUILDING: StackPlan = {
  stack_id: "platform-engineer",
  name: "Platform Engineer",
  requested_by: "ada@example.com",
  request_status: "pending",
  weeks_wanted: 10,
  step: "questions",
  next_step: "Submit Questions for each Lesson with submit_questions.",
  syllabus_draft: 4,
  syllabus_status: "pending",
  lessons: [
    { id: "w01-l01", title: "One", multiple_choice: 6, written: 2, ready: true },
    { id: "w01-l02", title: "Two", multiple_choice: 1, written: 0, ready: false },
  ],
  lessons_ready: 1,
  thin_concepts: [],
};

it("links to Add a Stack", async () => {
  stubApi({ "/me": ONBOARDED, "/stacks": STACKS });

  render(await StacksPage());

  expect(screen.getByRole("link", { name: "Add a Stack" }).getAttribute("href")).toBe(
    "/stacks/new",
  );
  expect(screen.queryByRole("heading", { name: "Stacks being built" })).toBeNull();
});

it("lists the Stacks being built, with their step and how to have Claude build them", async () => {
  stubApi({ "/me": ONBOARDED, "/stacks": STACKS, "/stack-requests": [BUILDING] });

  render(
    await StacksPage({
      params: Promise.resolve({}),
      searchParams: Promise.resolve({ requested: "platform-engineer" }),
    }),
  );

  expect(screen.getByRole("heading", { name: "Stacks being built" })).toBeTruthy();
  expect(screen.getByRole("status").textContent).toMatch(/Requested platform-engineer/);
  const steps = screen.getByRole("list", { name: "Steps" });
  expect(steps.querySelector('[aria-current="step"]')?.textContent).toBe("Quiz setup");
  expect(screen.getByText("1 of 2 Lessons have their Questions")).toBeTruthy();
  expect(screen.getByText("/mcp__interview-cracker__build_stack platform-engineer")).toBeTruthy();
  expect(screen.getByRole("button", { name: "Delete Platform Engineer" })).toBeTruthy();
});

it("lets only a Stack's requester or the Admin delete it", async () => {
  const theirs = { ...BUILDING, requested_by: "grace@example.com" };
  stubApi({ "/me": ONBOARDED, "/stacks": STACKS, "/stack-requests": [theirs] });
  render(await StacksPage());
  expect(screen.queryByRole("button", { name: /^Delete/ })).toBeNull();
  cleanup();

  stubApi({
    "/me": { ...ONBOARDED, is_admin: true },
    "/stacks": STACKS,
    "/stack-requests": [theirs],
  });
  render(await StacksPage());
  expect(screen.getByRole("button", { name: "Delete Platform Engineer" })).toBeTruthy();
});
