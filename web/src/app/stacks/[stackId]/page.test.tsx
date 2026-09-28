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
// React Flow needs a real layout engine; its layout is tested in WeekGraph.test.ts.
vi.mock("./WeekGraph", () => ({
  WeekGraph: ({ syllabus }: { syllabus: Syllabus }) => (
    <div role="figure" aria-label="Week graph">
      {syllabus.name}
    </div>
  ),
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
        {
          id: "w01-l01",
          title: "Names and objects",
          minutes: 60,
          state: "completed",
        },
        { id: "w01-l02", title: "Iterators", minutes: 60, state: "unlocked" },
      ],
      milestones: [
        {
          id: "w01-m01",
          title: "Build a CLI",
          kind: "build",
          minutes: 120,
          ticked: true,
        },
      ],
    },
    {
      id: "w02",
      number: 2,
      title: "LLM APIs",
      goal: "Call models.",
      deliverable: "A chat bot.",
      lessons: [
        { id: "w02-l01", title: "Messages API", minutes: 45, state: "locked" },
      ],
      milestones: [
        {
          id: "w02-m01",
          title: "Apply to one job",
          kind: "job-hunt",
          minutes: 30,
          ticked: false,
        },
      ],
    },
  ],
  removed_lessons: [],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

async function renderWeekMap(
  body: Syllabus = syllabus,
  view: "list" | "graph" = "list",
) {
  stubApi({ "/stacks/agentic-ai-engineer": body });
  render(
    await WeekMapPage({
      params: Promise.resolve({ stackId: "agentic-ai-engineer" }),
      searchParams: Promise.resolve(view === "list" ? { view } : {}),
    } as never),
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
  expect(lessons(1)).toEqual([
    "Completed Names and objects",
    "Unlocked Iterators",
  ]);
  expect(lessons(2)).toEqual(["Locked Messages API"]);
});

it("links every Lesson, Locked ones too, so a Learner can read ahead", async () => {
  await renderWeekMap();

  expect(
    screen.getByRole("link", { name: "Messages API" }).getAttribute("href"),
  ).toBe("/stacks/agentic-ai-engineer/lessons/w02-l01");
});

it("shows each Week's Milestones as a checklist with the Learner's ticks", async () => {
  await renderWeekMap();

  const checkboxes = (n: number) =>
    within(week(n))
      .getAllByRole("checkbox")
      .map((c) => [
        c.closest("li")?.textContent,
        (c as HTMLInputElement).checked,
      ]);
  expect(checkboxes(1)).toEqual([["Build Build a CLI", true]]);
  expect(checkboxes(2)).toEqual([["Job hunt Apply to one job", false]]);
});

it("links to Review, which is optional and locks nothing", async () => {
  await renderWeekMap();

  expect(
    screen.getByRole("link", { name: "Review" }).getAttribute("href"),
  ).toBe("/review");
  expect(screen.queryByText(/Streak/)).toBeNull();
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
          { id: "w01-new", title: "Generators", minutes: 30, state: "updated" },
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

  const history = screen.getByRole("region", {
    name: "Completed, no longer in the Syllabus",
  });
  expect(
    within(history)
      .getAllByRole("listitem")
      .map((li) => li.textContent),
  ).toEqual(["Old setup.py packaging · Syllabus v2026-09-01"]);
  expect(within(history).queryByRole("link")).toBeNull();
});

it("shows no history section when no Completed Lesson was removed", async () => {
  await renderWeekMap();

  expect(
    screen.queryByRole("region", {
      name: "Completed, no longer in the Syllabus",
    }),
  ).toBeNull();
});

it("opens as a graph by default, with a toggle to the list", async () => {
  await renderWeekMap(syllabus, "graph");

  expect(screen.getByRole("figure", { name: "Week graph" })).toBeTruthy();
  expect(screen.queryByRole("list", { name: "Lessons" })).toBeNull();
  const toggle = screen.getByRole("navigation", { name: "Week map view" });
  expect(
    within(toggle)
      .getByRole("link", { name: "Graph" })
      .getAttribute("aria-current"),
  ).toBe("page");
  expect(
    within(toggle).getByRole("link", { name: "List" }).getAttribute("href"),
  ).toBe("/stacks/agentic-ai-engineer?view=list");
});

it("shows the list, with Milestones to tick, when the Learner picks List", async () => {
  await renderWeekMap();

  expect(screen.queryByRole("figure", { name: "Week graph" })).toBeNull();
  expect(
    screen.getByRole("link", { name: "List" }).getAttribute("aria-current"),
  ).toBe("page");
  expect(screen.getByRole("link", { name: "Graph" }).getAttribute("href")).toBe(
    "/stacks/agentic-ai-engineer",
  );
});
