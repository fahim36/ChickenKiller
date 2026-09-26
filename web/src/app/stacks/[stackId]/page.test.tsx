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

/** A Lesson no Pending Review Round is holding back. */
const noReview = { waiting_for_review: false };

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
        { ...noReview, id: "w01-l01", title: "Names and objects", minutes: 60, state: "completed" },
        { ...noReview, id: "w01-l02", title: "Iterators", minutes: 60, state: "unlocked" },
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
      lessons: [{ ...noReview, id: "w02-l01", title: "Messages API", minutes: 45, state: "locked" }],
      milestones: [
        { id: "w02-m01", title: "Apply to one job", kind: "job-hunt", minutes: 30, ticked: false },
      ],
    },
  ],
  daily_review: null,
  removed_lessons: [],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function renderWeekMap(body: Syllabus = syllabus) {
  stubApi({ "/stacks/agentic-ai-engineer": body });
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

it("shows no Daily Review on a day with nothing owed", async () => {
  await renderWeekMap();

  expect(screen.queryByRole("region", { name: "Daily Review" })).toBeNull();
});

it("shows today's pending Review Round and says which Lesson waits for it", async () => {
  const [first, second] = syllabus.weeks[0].lessons;
  await renderWeekMap({
    ...syllabus,
    weeks: [
      {
        ...syllabus.weeks[0],
        lessons: [first, { ...second, state: "locked", waiting_for_review: true }],
      },
      syllabus.weeks[1],
    ],
    daily_review: {
      day: "2026-09-26",
      rounds: [
        {
          id: "round-1",
          number: 1,
          state: "pending",
          opened_at: "2026-09-26T04:00:00Z",
          pending_at: "2026-09-26T06:00:00Z",
          finished_at: null,
          answered: 0,
          total: 10,
        },
      ],
    },
  });

  expect(screen.getByRole("region", { name: "Daily Review" }).textContent).toContain(
    "Review Round 1 is pending: finish it to unlock your next Lesson.",
  );
  const iterators = screen.getByRole("link", { name: "Iterators" }).closest("li");
  expect(iterators?.textContent).toBe("Locked Iterators · Finish your Review Round to unlock");
});

it("marks Updated Lessons, which a Syllabus Update changed or added behind the Learner", async () => {
  const [first, second] = syllabus.weeks[0].lessons;
  await renderWeekMap({
    ...syllabus,
    weeks: [
      {
        ...syllabus.weeks[0],
        lessons: [
          { ...first, state: "updated" },
          { ...noReview, id: "w01-new", title: "Generators", minutes: 30, state: "updated" },
          second,
        ],
      },
      syllabus.weeks[1],
    ],
  });

  const lessons = within(within(week(1)).getByRole("list", { name: "Lessons" }))
    .getAllByRole("listitem")
    .map((li) => li.textContent);
  expect(lessons).toEqual([
    "Updated Names and objects",
    "Updated Generators",
    "Unlocked Iterators",
  ]);
});

it("keeps Completed Lessons a Syllabus Update removed in the Learner's history", async () => {
  await renderWeekMap({
    ...syllabus,
    removed_lessons: [
      {
        id: "w01-l00",
        title: "Old `setup.py` packaging",
        completed_at: "2026-09-20T10:00:00Z",
        version: "v2026-09-01",
      },
    ],
  });

  const history = screen.getByRole("region", { name: "Completed, no longer in the Syllabus" });
  expect(within(history).getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    "Old setup.py packaging · Syllabus v2026-09-01",
  ]);
  expect(within(history).queryByRole("link")).toBeNull();
});

it("shows no history section when no Completed Lesson was removed", async () => {
  await renderWeekMap();

  expect(screen.queryByRole("region", { name: "Completed, no longer in the Syllabus" })).toBeNull();
});
