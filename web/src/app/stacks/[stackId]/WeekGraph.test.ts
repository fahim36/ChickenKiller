import { expect, it } from "vitest";
import type { Syllabus } from "@/lib/api";
import { weekGraphLayout } from "./WeekGraph";

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
      milestones: [],
    },
  ],
  removed_lessons: [],
};

it("puts each Week on its own row: hub, then Lessons in order, then Milestones", () => {
  const { nodes } = weekGraphLayout(syllabus);

  const row = (y: number) =>
    nodes
      .filter((n) => n.position.y === y)
      .sort((a, b) => a.position.x - b.position.x)
      .map((n) => n.id);
  expect(row(0)).toEqual([
    "week:w01",
    "lesson:w01-l01",
    "lesson:w01-l02",
    "milestone:w01-m01",
  ]);
  expect(row(nodes.find((n) => n.id === "week:w02")!.position.y)).toEqual([
    "week:w02",
    "lesson:w02-l01",
  ]);
});

it("links every Lesson node to its page, Locked ones too", () => {
  const { nodes } = weekGraphLayout(syllabus);

  const locked = nodes.find((n) => n.id === "lesson:w02-l01");
  expect(locked?.type === "lesson" && locked.data.href).toBe(
    "/stacks/agentic-ai-engineer/lessons/w02-l01",
  );
  expect(
    nodes
      .filter((n) => n.type === "lesson")
      .every((n) => n.style?.pointerEvents === "all"),
  ).toBe(true);
});

it("chains the Week hubs and animates the edge into the Unlocked Lesson", () => {
  const { edges } = weekGraphLayout(syllabus);

  expect(edges.map((e) => e.id)).toEqual([
    "week:w01->lesson:w01-l01",
    "lesson:w01-l01->lesson:w01-l02",
    "lesson:w01-l02->milestone:w01-m01",
    "week:w01->week:w02",
    "week:w02->lesson:w02-l01",
  ]);
  expect(edges.filter((e) => e.animated).map((e) => e.target)).toEqual([
    "lesson:w01-l02",
  ]);
});

it("opens on the current Week, around its Unlocked Lesson", () => {
  expect(weekGraphLayout(syllabus).focus).toEqual([
    "week:w01",
    "lesson:w01-l01",
    "lesson:w01-l02",
  ]);
});
