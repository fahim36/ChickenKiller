import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import type { Syllabus } from "@/lib/api";
import { stubApi } from "@/test/stubApi";
import WeekMapPage from "./page";

vi.mock("next/server", () => ({ connection: async () => {} }));
vi.mock("next/cache", () => ({ refresh: () => {} }));
vi.mock("@clerk/nextjs/server", () => ({
  auth: async () => ({ getToken: async () => "session-token" }),
}));

const syllabus: Syllabus = {
  id: "agentic-ai-engineer",
  name: "Agentic AI Engineer",
  summary: "Agents.",
  version: "v2026-09-26",
  weeks: [
    {
      id: "w01",
      number: 1,
      title: "Python internals",
      goal: "Know Python.",
      deliverable: "A CLI.",
      lessons: [
        { id: "w01-l01", title: "Names and objects", minutes: 60, state: "completed" },
        { id: "w01-l02", title: "Iterators", minutes: 60, state: "unlocked" },
      ],
      milestones: [
        { id: "w01-m01", title: "Build a CLI", kind: "build", minutes: 120, ticked: true },
      ],
    },
    {
      id: "w02",
      number: 2,
      title: "LLM APIs",
      goal: "Call models.",
      deliverable: "A chat bot.",
      lessons: [{ id: "w02-l01", title: "Messages API", minutes: 45, state: "locked" }],
      milestones: [
        { id: "w02-m01", title: "Apply to one job", kind: "job-hunt", minutes: 30, ticked: false },
      ],
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function renderWeekMap() {
  stubApi({ "/stacks/agentic-ai-engineer": syllabus });
  render(
    await WeekMapPage({ params: Promise.resolve({ stackId: "agentic-ai-engineer" }) } as never),
  );
}

const week = (number: number) =>
  screen.getByRole("region", { name: new RegExp(`^Week ${number}:`) });

it("shows each Week's Lessons with their states, in Syllabus order", async () => {
  await renderWeekMap();

  const lessons = (n: number) =>
    within(within(week(n)).getByRole("list", { name: "Lessons" }))
      .getAllByRole("listitem")
      .map((li) => li.textContent);
  expect(lessons(1)).toEqual(["Completed Names and objects", "Unlocked Iterators"]);
  expect(lessons(2)).toEqual(["Locked Messages API"]);
});

it("links every Lesson, Locked ones too, so a Learner can read ahead", async () => {
  await renderWeekMap();

  expect(screen.getByRole("link", { name: "Messages API" }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer/lessons/w02-l01",
  );
});

it("shows each Week's Milestones as a checklist with the Learner's ticks", async () => {
  await renderWeekMap();

  const checkboxes = (n: number) =>
    within(week(n))
      .getAllByRole("checkbox")
      .map((c) => [c.closest("li")?.textContent, (c as HTMLInputElement).checked]);
  expect(checkboxes(1)).toEqual([["Build Build a CLI", true]]);
  expect(checkboxes(2)).toEqual([["Job hunt Apply to one job", false]]);
});
